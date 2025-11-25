"""TMDB API Client."""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import config
from ..utils import setup_logger
from .rate_limiter import RateLimiter


logger = setup_logger(__name__, config.LOGS_DIR / "api.log", config.LOG_LEVEL)


class TMDBAPIError(Exception):
    """Custom exception for TMDB API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TMDBAPIClient:
    """Client for TMDB API."""

    def __init__(self):
        """Initialize API client."""
        self.base_url = config.TMDB_API_BASE_URL
        self.api_key = config.TMDB_API_KEY
        self.rate_limiter = RateLimiter(rate=config.RATE_LIMIT, per=1.0)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Validate API key
        if not self.api_key:
            raise ValueError("TMDB API key is not configured")

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _make_request(self, endpoint: str) -> Dict[Any, Any]:
        """Make API request with retry logic."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self.rate_limiter.acquire()

        url = f"{self.base_url}/{endpoint}"
        logger.debug(f"Fetching: {url}")

        try:
            async with self.session.get(url) as response:
                if response.status == 429:
                    # Rate limit exceeded, wait and retry
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limit exceeded. Waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientError("Rate limit exceeded")
                
                if response.status == 404:
                    logger.warning(f"Resource not found: {endpoint}")
                    raise TMDBAPIError(f"Resource not found: {endpoint}", status_code=404)
                
                if response.status == 401:
                    logger.error("Invalid API key")
                    raise TMDBAPIError("Invalid API key", status_code=401)

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientResponseError as e:
            logger.error(f"API request failed for {endpoint}: HTTP {e.status} - {e.message}")
            raise TMDBAPIError(f"HTTP {e.status}: {e.message}", status_code=e.status)
        except aiohttp.ClientError as e:
            logger.error(f"API request failed for {endpoint}: {str(e)}")
            raise

    async def get_movie_details(self, movie_id: int) -> Dict[Any, Any]:
        """
        Get movie details with appended responses.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Movie data dictionary
        """
        endpoint = f"movie/{movie_id}"
        params = "append_to_response=credits,external_ids,keywords,watch/providers,translations,similar"
        return await self._make_request(f"{endpoint}?{params}")

    async def get_tv_series_details(self, series_id: int) -> Dict[Any, Any]:
        """
        Get TV series details with appended responses.

        Args:
            series_id: TMDB TV series ID

        Returns:
            TV series data dictionary
        """
        endpoint = f"tv/{series_id}"
        params = "append_to_response=credits,external_ids,keywords,watch/providers,translations,similar"
        return await self._make_request(f"{endpoint}?{params}")
