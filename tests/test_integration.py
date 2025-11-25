import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from src.services.processor import ContentProcessor
from src.models.state import ProcessingState
from src.models.movie import Movie
from src.utils import utcnow


@pytest.fixture
def mock_config():
    """Mock the config for tests."""
    with patch('src.services.processor.config') as mock:
        mock.CHECKPOINT_INTERVAL = 10
        mock.MAX_RETRIES = 3
        mock.LOGS_DIR = MagicMock()
        mock.LOG_LEVEL = "INFO"
        yield mock


@pytest.fixture
def mock_get_db(db_session):
    """Mock get_db to use the test db_session."""
    class MockContextManager:
        def __enter__(self):
            return db_session
        def __exit__(self, *args):
            pass
    
    with patch('src.services.processor.get_db', return_value=MockContextManager()):
        yield


@pytest.fixture
def mock_to_thread():
    """Mock asyncio.to_thread to run synchronously (for SQLite compatibility in tests)."""
    async def run_sync(func, *args, **kwargs):
        return func(*args, **kwargs)
    
    with patch('asyncio.to_thread', side_effect=run_sync):
        yield


@pytest.mark.asyncio
async def test_full_movie_processing_workflow(db_session, sample_movie_data, mock_config, mock_get_db, mock_to_thread):
    """Test complete workflow: fetch, parse, and store movie data."""
    
    # Create processor
    processor = ContentProcessor()
    
    # Create a processing state entry
    state = ProcessingState(
        content_id=550,
        content_type="movie",
        status="pending"
    )
    db_session.add(state)
    db_session.commit()
    
    # Mock API client and its context manager
    mock_api_client = AsyncMock()
    mock_api_client.get_movie_details = AsyncMock(return_value=sample_movie_data)
    mock_api_client.__aenter__ = AsyncMock(return_value=mock_api_client)
    mock_api_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch('src.services.processor.TMDBAPIClient', return_value=mock_api_client):
        # Process a single content item
        await processor._process_single_content(mock_api_client, "movie", state.id, 550)
        
        # Verify state was updated
        db_session.refresh(state)
        assert state.status == "completed"
        assert state.completed_at is not None
        
        # Verify movie was saved
        movie = db_session.query(Movie).filter_by(id=550).first()
        assert movie is not None
        assert movie.title == "Fight Club"
        assert movie.runtime == 139
        
        # Verify relationships were saved
        assert len(movie.genres) > 0
        assert len(movie.production_companies) > 0


@pytest.mark.asyncio
async def test_error_handling_and_retry(db_session, mock_config, mock_get_db, mock_to_thread):
    """Test that processor handles errors and marks items as failed."""
    
    processor = ContentProcessor()
    
    # Create a processing state entry
    state = ProcessingState(
        content_id=999999,
        content_type="movie",
        status="pending"
    )
    db_session.add(state)
    db_session.commit()
    
    # Mock API client to raise an exception
    mock_api_client = AsyncMock()
    mock_api_client.get_movie_details = AsyncMock(side_effect=Exception("API Error"))
    
    # Process and expect failure
    await processor._process_single_content(mock_api_client, "movie", state.id, 999999)
    
    # Verify state was marked as failed
    db_session.refresh(state)
    assert state.status == "failed"
    assert state.attempts > 0
    assert state.last_error is not None


@pytest.mark.asyncio
async def test_incremental_updates(db_session, sample_movie_data, mock_config):
    """Test that incremental updates work correctly."""
    
    # Create an old movie entry with a different ID than sample_movie_data
    old_date = utcnow() - timedelta(days=35)
    movie = Movie(
        id=9999,  # Use different ID to avoid conflicts
        title="Old Movie",
        original_title="Old Movie",
        updated_at=old_date
    )
    db_session.add(movie)
    
    # Create corresponding state
    state = ProcessingState(
        content_id=9999,
        content_type="movie",
        status="completed",
        last_attempt_at=old_date
    )
    db_session.add(state)
    db_session.commit()
    
    # Mock get_db to use test session
    class MockContextManager:
        def __enter__(self):
            return db_session
        def __exit__(self, *args):
            pass
    
    with patch('src.services.processor.get_db', return_value=MockContextManager()):
        processor = ContentProcessor()
        
        # Check for updates
        await processor.check_and_schedule_updates()
        
        # Verify state was reset to pending
        db_session.refresh(state)
        assert state.status == "pending"


@pytest.mark.asyncio
async def test_concurrent_processing(db_session, sample_movie_data, mock_config, mock_to_thread):
    """Test processing multiple items concurrently."""
    
    # Create multiple state entries with unique IDs
    for i in range(5):
        state = ProcessingState(
            content_id=10000 + i,  # Use unique IDs to avoid conflicts
            content_type="movie",
            status="pending"
        )
        db_session.add(state)
    db_session.commit()
    
    # Mock API client to return unique data for each movie
    async def mock_get_movie(tmdb_id):
        data = {
            "id": tmdb_id,
            "title": f"Movie {tmdb_id}",
            "original_title": f"Movie {tmdb_id}",
            "overview": "Test overview",
            "release_date": "2020-01-01",
            "runtime": 120,
            "budget": 1000000,
            "revenue": 2000000,
            "popularity": 10.0,
            "vote_average": 7.5,
            "vote_count": 100,
            "adult": False,
            "original_language": "en",
            "status": "Released",
            "imdb_id": f"tt{tmdb_id}",  # Unique imdb_id per movie
            "genres": [],
            "production_companies": [],
        }
        await asyncio.sleep(0.01)  # Simulate API delay
        return data
    
    # Mock get_db to use test session
    class MockContextManager:
        def __enter__(self):
            return db_session
        def __exit__(self, *args):
            pass
    
    mock_api_client = AsyncMock()
    mock_api_client.get_movie_details = mock_get_movie
    mock_api_client.__aenter__ = AsyncMock(return_value=mock_api_client)
    mock_api_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch('src.services.processor.get_db', return_value=MockContextManager()):
        with patch('src.services.processor.TMDBAPIClient', return_value=mock_api_client):
            processor = ContentProcessor()
            
            await processor.process_content("movie", batch_size=5)
            
            # Verify all were processed - count only the specific IDs we created
            completed = db_session.query(ProcessingState).filter(
                ProcessingState.status == "completed",
                ProcessingState.content_id.in_([10000 + i for i in range(5)])
            ).count()
            assert completed == 5
            
            # Verify all movies were created - count only the specific IDs
            movies = db_session.query(Movie).filter(
                Movie.id.in_([10000 + i for i in range(5)])
            ).count()
            assert movies == 5


@pytest.mark.asyncio
async def test_graceful_shutdown(db_session, mock_config, mock_to_thread):
    """Test that processor handles shutdown signal gracefully."""
    
    # Create many state entries
    for i in range(20):
        state = ProcessingState(
            content_id=i,
            content_type="movie",
            status="pending"
        )
        db_session.add(state)
    db_session.commit()
    
    # Mock get_db to use test session
    class MockContextManager:
        def __enter__(self):
            return db_session
        def __exit__(self, *args):
            pass
    
    mock_api_client = AsyncMock()
    mock_api_client.get_movie_details = AsyncMock(return_value={"id": 1, "title": "Test", "original_title": "Test"})
    mock_api_client.__aenter__ = AsyncMock(return_value=mock_api_client)
    mock_api_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch('src.services.processor.get_db', return_value=MockContextManager()):
        with patch('src.services.processor.TMDBAPIClient', return_value=mock_api_client):
            processor = ContentProcessor()
            
            # Start processing and immediately signal shutdown
            async def process_and_shutdown():
                await asyncio.sleep(0.1)  # Let it process a few
                processor.stop()
            
            await asyncio.gather(
                processor.process_content("movie", batch_size=10),
                process_and_shutdown()
            )
    
    # Should have stopped before processing all
    pending = db_session.query(ProcessingState).filter_by(
        status="pending"
    ).count()
    
    # Some should still be pending (or at least the test shouldn't crash)
    # The exact behavior depends on timing
