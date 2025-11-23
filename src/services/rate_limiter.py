"""Rate limiter for API requests."""
import asyncio
import time
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int = 29, per: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            rate: Number of requests allowed per time period
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request."""
        async with self.lock:
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current

            # Add new tokens based on time passed
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate

            # Wait if no tokens available
            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
                await asyncio.sleep(sleep_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0
