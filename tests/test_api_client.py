import pytest
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
from src.services.api_client import TMDBAPIClient
from src.services.rate_limiter import RateLimiter


@pytest.fixture
def api_client():
    """Create API client with test configuration."""
    return TMDBAPIClient(api_key="test_api_key")


@pytest.mark.asyncio
async def test_api_client_initialization(api_client):
    """Test that API client initializes correctly."""
    assert api_client.api_key == "test_api_key"
    assert api_client.base_url == "https://api.themoviedb.org/3"
    assert isinstance(api_client.rate_limiter, RateLimiter)


@pytest.mark.asyncio
async def test_get_movie_details_success(api_client, sample_movie_data):
    """Test successful movie details retrieval."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_movie_data)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await api_client.get_movie_details(550)
        
        assert result is not None
        assert result["id"] == 550
        assert result["title"] == "Fight Club"


@pytest.mark.asyncio
async def test_get_movie_details_not_found(api_client):
    """Test handling of 404 response."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await api_client.get_movie_details(999999)
        
        assert result is None


@pytest.mark.asyncio
async def test_get_movie_details_rate_limited(api_client, sample_movie_data):
    """Test handling of rate limit (429) response."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        # First call returns 429, second succeeds
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {"Retry-After": "1"}
        
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value=sample_movie_data)
        
        mock_get.return_value.__aenter__.side_effect = [
            mock_response_429,
            mock_response_200
        ]
        
        result = await api_client.get_movie_details(550)
        
        # Should succeed after retry
        assert result is not None
        assert result["id"] == 550


@pytest.mark.asyncio
async def test_get_tv_series_details_success(api_client, sample_tv_data):
    """Test successful TV series details retrieval."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_tv_data)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await api_client.get_tv_series_details(1396)
        
        assert result is not None
        assert result["id"] == 1396
        assert result["name"] == "Breaking Bad"


@pytest.mark.asyncio
async def test_api_client_uses_bearer_token(api_client):
    """Test that API client uses Bearer token authentication."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"id": 123})
        mock_get.return_value.__aenter__.return_value = mock_response
        
        await api_client.get_movie_details(123)
        
        # Check that Bearer token was used in Authorization header
        call_kwargs = mock_get.call_args.kwargs
        assert "headers" in call_kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test_api_key"


@pytest.mark.asyncio
async def test_api_client_handles_network_error(api_client):
    """Test handling of network errors."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = aiohttp.ClientError("Network error")
        
        result = await api_client.get_movie_details(123)
        
        # Should return None on error after retries
        assert result is None


@pytest.mark.asyncio
async def test_api_client_close(api_client):
    """Test that API client closes session properly."""
    with patch.object(api_client.session, 'close', new_callable=AsyncMock) as mock_close:
        await api_client.close()
        mock_close.assert_called_once()
