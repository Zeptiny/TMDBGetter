import pytest
import aiohttp
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.services.api_client import TMDBAPIClient, TMDBAPIError
from src.services.rate_limiter import RateLimiter


@pytest.fixture
def mock_env():
    """Set up mock environment variables."""
    with patch.dict(os.environ, {"TMDB_API_KEY": "test_api_key", "DB_PASSWORD": "test"}):
        yield


@pytest.fixture
def api_client(mock_env):
    """Create API client with test configuration."""
    # Patch the config to use test values
    with patch('src.services.api_client.config') as mock_config:
        mock_config.TMDB_API_BASE_URL = "https://api.themoviedb.org/3"
        mock_config.TMDB_API_KEY = "test_api_key"
        mock_config.RATE_LIMIT = 30
        mock_config.LOGS_DIR = MagicMock()
        mock_config.LOG_LEVEL = "INFO"
        return TMDBAPIClient()


@pytest.mark.asyncio
async def test_api_client_initialization(api_client):
    """Test that API client initializes correctly."""
    assert api_client.api_key == "test_api_key"
    assert api_client.base_url == "https://api.themoviedb.org/3"
    assert isinstance(api_client.rate_limiter, RateLimiter)


@pytest.mark.asyncio
async def test_get_movie_details_success(api_client, sample_movie_data):
    """Test successful movie details retrieval."""
    async with api_client:
        with patch.object(api_client.session, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_movie_data)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_get.return_value = mock_response
            
            result = await api_client.get_movie_details(550)
            
            assert result is not None
            assert result["id"] == 550
            assert result["title"] == "Fight Club"


@pytest.mark.asyncio
async def test_get_movie_details_not_found(api_client):
    """Test handling of 404 response."""
    async with api_client:
        with patch.object(api_client.session, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_get.return_value = mock_response
            
            with pytest.raises(TMDBAPIError) as exc_info:
                await api_client.get_movie_details(999999)
            
            assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_movie_details_rate_limited(api_client, sample_movie_data):
    """Test handling of rate limit (429) response."""
    async with api_client:
        with patch.object(api_client.session, 'get') as mock_get:
            # First call returns 429, subsequent calls succeed
            call_count = [0]
            
            async def mock_response_factory(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_response = AsyncMock()
                    mock_response.status = 429
                    mock_response.headers = {"Retry-After": "1"}
                    return mock_response
                else:
                    mock_response = AsyncMock()
                    mock_response.status = 200
                    mock_response.json = AsyncMock(return_value=sample_movie_data)
                    return mock_response
            
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = mock_response_factory
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_get.return_value = mock_ctx
            
            # Due to retry logic, should eventually succeed
            result = await api_client.get_movie_details(550)
            
            # Should succeed after retry
            assert result is not None
            assert result["id"] == 550


@pytest.mark.asyncio
async def test_get_tv_series_details_success(api_client, sample_tv_data):
    """Test successful TV series details retrieval."""
    async with api_client:
        with patch.object(api_client.session, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_tv_data)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_get.return_value = mock_response
            
            result = await api_client.get_tv_series_details(1396)
            
            assert result is not None
            assert result["id"] == 1396
            assert result["name"] == "Breaking Bad"


@pytest.mark.asyncio
async def test_api_client_uses_bearer_token(mock_env):
    """Test that API client uses Bearer token authentication."""
    with patch('src.services.api_client.config') as mock_config:
        mock_config.TMDB_API_BASE_URL = "https://api.themoviedb.org/3"
        mock_config.TMDB_API_KEY = "test_api_key"
        mock_config.RATE_LIMIT = 30
        mock_config.LOGS_DIR = MagicMock()
        mock_config.LOG_LEVEL = "INFO"
        
        client = TMDBAPIClient()
        async with client:
            # The Authorization header should be set in the session
            assert "Authorization" in client.session._default_headers
            assert client.session._default_headers["Authorization"] == "Bearer test_api_key"


@pytest.mark.asyncio
async def test_api_client_handles_network_error(api_client):
    """Test handling of network errors - should raise RetryError after all retries fail."""
    import tenacity
    
    async with api_client:
        with patch.object(api_client.session, 'get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Network error")
            
            # After retries are exhausted, tenacity raises RetryError
            with pytest.raises(tenacity.RetryError):
                await api_client.get_movie_details(123)


@pytest.mark.asyncio
async def test_api_client_context_manager(mock_env):
    """Test that API client works as context manager."""
    with patch('src.services.api_client.config') as mock_config:
        mock_config.TMDB_API_BASE_URL = "https://api.themoviedb.org/3"
        mock_config.TMDB_API_KEY = "test_api_key"
        mock_config.RATE_LIMIT = 30
        mock_config.LOGS_DIR = MagicMock()
        mock_config.LOG_LEVEL = "INFO"
        
        client = TMDBAPIClient()
        
        # Before entering context, session should be None
        assert client.session is None
        
        async with client:
            # Inside context, session should be set
            assert client.session is not None
        
        # After exiting context, session should be closed
        # (session.close() called, but object still exists)
