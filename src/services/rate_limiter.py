"""Rate limiter for API requests."""
import asyncio
import time
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter optimized for high throughput."""

    def __init__(self, rate: int = 30, per: float = 1.0, requests_per_second: Optional[int] = None):
        """
        Initialize rate limiter.

        Args:
            rate: Number of requests allowed per time period
            per: Time period in seconds
            requests_per_second: Alias for rate (for backwards compatibility with tests)
        """
        # Support both parameter styles
        if requests_per_second is not None:
            rate = requests_per_second
        
        self.rate = rate
        self.capacity = rate  # Maximum tokens (for test compatibility)
        self.per = per
        self.tokens = float(rate)  # Current tokens (for test compatibility)
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()
        
        # Pre-calculate refill rate for efficiency
        self._refill_rate = rate / per  # tokens per second

    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.monotonic()
        time_passed = now - self.last_refill
        self.last_refill = now
        
        # Add new tokens based on time passed
        self.tokens = min(self.capacity, self.tokens + time_passed * self._refill_rate)

    async def acquire(self):
        """Acquire permission to make a request. Waits if necessary."""
        async with self.lock:
            self._refill()
            
            # If we have at least 1 token, consume it immediately
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            
            # Calculate wait time needed to get 1 token
            tokens_needed = 1.0 - self.tokens
            wait_time = tokens_needed / self._refill_rate
            
            # Wait for token to become available
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # Refill and consume
            self._refill()
            self.tokens = max(0.0, self.tokens - 1.0)

    @property
    def allowance(self) -> float:
        """Alias for tokens (backwards compatibility)."""
        return self.tokens
    
    @allowance.setter
    def allowance(self, value: float):
        """Alias for tokens (backwards compatibility)."""
        self.tokens = value
