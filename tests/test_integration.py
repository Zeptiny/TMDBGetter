import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from src.services.processor import ContentProcessor
from src.models.state import ProcessingState, ProcessingStatus
from src.models.movie import Movie


@pytest.mark.asyncio
async def test_full_movie_processing_workflow(db_session, sample_movie_data):
    """Test complete workflow: fetch, parse, and store movie data."""
    
    # Create processor
    processor = ContentProcessor(
        db_session=db_session,
        api_key="test_key",
        batch_size=1,
        max_workers=1
    )
    
    # Create a processing state entry
    state = ProcessingState(
        content_id=550,
        content_type="movie",
        status=ProcessingStatus.PENDING
    )
    db_session.add(state)
    db_session.commit()
    
    # Mock API client to return sample data
    with patch.object(processor.api_client, 'get_movie_details', 
                      new_callable=AsyncMock) as mock_get:
        mock_get.return_value = sample_movie_data
        
        # Process content
        await processor.process_content()
        
        # Verify state was updated
        db_session.refresh(state)
        assert state.status == ProcessingStatus.COMPLETED
        assert state.last_fetched is not None
        
        # Verify movie was saved
        movie = db_session.query(Movie).filter_by(tmdb_id=550).first()
        assert movie is not None
        assert movie.title == "Fight Club"
        assert movie.runtime == 139
        
        # Verify relationships were saved
        assert len(movie.genres) > 0
        assert len(movie.production_companies) > 0


@pytest.mark.asyncio
async def test_error_handling_and_retry(db_session):
    """Test that processor handles errors and marks items as failed."""
    
    processor = ContentProcessor(
        db_session=db_session,
        api_key="test_key",
        batch_size=1,
        max_workers=1
    )
    
    # Create a processing state entry
    state = ProcessingState(
        content_id=999999,
        content_type="movie",
        status=ProcessingStatus.PENDING
    )
    db_session.add(state)
    db_session.commit()
    
    # Mock API client to return None (simulating 404)
    with patch.object(processor.api_client, 'get_movie_details',
                      new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        
        await processor.process_content()
        
        # Verify state was marked as failed
        db_session.refresh(state)
        assert state.status == ProcessingStatus.FAILED
        assert state.attempts > 0
        assert state.error_message is not None


@pytest.mark.asyncio
async def test_incremental_updates(db_session, sample_movie_data):
    """Test that incremental updates work correctly."""
    from datetime import datetime, timedelta
    
    processor = ContentProcessor(
        db_session=db_session,
        api_key="test_key"
    )
    
    # Create an old movie entry
    old_date = datetime.utcnow() - timedelta(days=35)
    movie = Movie(
        tmdb_id=550,
        title="Fight Club - Old",
        original_title="Fight Club",
        updated_at=old_date
    )
    db_session.add(movie)
    
    # Create corresponding state
    state = ProcessingState(
        content_id=550,
        content_type="movie",
        status=ProcessingStatus.COMPLETED,
        last_attempt_at=old_date
    )
    db_session.add(state)
    db_session.commit()
    
    # Check for updates
    updates_needed = await processor.check_and_schedule_updates()
    
    # Should identify this movie for update
    assert updates_needed > 0
    
    # Verify state was reset to pending
    db_session.refresh(state)
    assert state.status == ProcessingStatus.PENDING


@pytest.mark.asyncio
async def test_concurrent_processing(db_session, sample_movie_data):
    """Test processing multiple items concurrently."""
    
    processor = ContentProcessor(
        db_session=db_session,
        api_key="test_key",
        batch_size=5,
        max_workers=3
    )
    
    # Create multiple state entries
    for i in range(5):
        state = ProcessingState(
            content_id=500 + i,
            content_type="movie",
            status=ProcessingStatus.PENDING
        )
        db_session.add(state)
    db_session.commit()
    
    # Mock API client
    async def mock_get_movie(tmdb_id):
        data = sample_movie_data.copy()
        data["id"] = tmdb_id
        data["title"] = f"Movie {tmdb_id}"
        await asyncio.sleep(0.1)  # Simulate API delay
        return data
    
    with patch.object(processor.api_client, 'get_movie_details',
                      side_effect=mock_get_movie):
        
        await processor.process_content()
        
        # Verify all were processed
        completed = db_session.query(ProcessingState).filter_by(
            status=ProcessingStatus.COMPLETED
        ).count()
        assert completed == 5
        
        # Verify all movies were created
        movies = db_session.query(Movie).count()
        assert movies == 5


@pytest.mark.asyncio
async def test_graceful_shutdown(db_session):
    """Test that processor handles shutdown signal gracefully."""
    
    processor = ContentProcessor(
        db_session=db_session,
        api_key="test_key",
        batch_size=10,
        max_workers=2
    )
    
    # Create many state entries
    for i in range(20):
        state = ProcessingState(
            content_id=i,
            content_type="movie",
            status=ProcessingStatus.PENDING
        )
        db_session.add(state)
    db_session.commit()
    
    # Start processing and immediately signal shutdown
    async def process_and_shutdown():
        await asyncio.sleep(0.5)  # Let it process a few
        processor.stop()
    
    with patch.object(processor.api_client, 'get_movie_details',
                      new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"id": 1, "title": "Test"}
        
        await asyncio.gather(
            processor.process_content(),
            process_and_shutdown()
        )
    
    # Should have stopped before processing all
    pending = db_session.query(ProcessingState).filter_by(
        status=ProcessingStatus.PENDING
    ).count()
    
    # Some should still be pending
    assert pending > 0
