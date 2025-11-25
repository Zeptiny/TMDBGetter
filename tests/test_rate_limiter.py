import pytest
import asyncio
from src.services.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_initialization():
    """Test that rate limiter initializes correctly."""
    limiter = RateLimiter(requests_per_second=10)
    assert limiter.rate == 10
    assert limiter.capacity == 10
    assert limiter.tokens == 10.0


@pytest.mark.asyncio
async def test_rate_limiter_allows_requests():
    """Test that rate limiter allows requests within limit."""
    limiter = RateLimiter(requests_per_second=10)
    
    # Should allow immediate request
    await limiter.acquire()
    assert limiter.tokens < 10


@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_depleted():
    """Test that rate limiter blocks when tokens are depleted."""
    limiter = RateLimiter(requests_per_second=5)
    
    # Deplete all tokens
    for _ in range(5):
        await limiter.acquire()
    
    # Should have no tokens left
    assert limiter.tokens < 1
    
    # Next request should wait
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start
    
    # Should have waited at least some time
    assert elapsed > 0


@pytest.mark.asyncio
async def test_rate_limiter_refills_over_time():
    """Test that rate limiter refills tokens over time."""
    limiter = RateLimiter(requests_per_second=10)
    
    # Use some tokens
    await limiter.acquire()
    tokens_after_acquire = limiter.tokens
    
    # Wait a bit
    await asyncio.sleep(0.2)
    
    # Tokens should have refilled
    limiter._refill()
    assert limiter.tokens > tokens_after_acquire


@pytest.mark.asyncio
async def test_rate_limiter_concurrent_requests():
    """Test rate limiter with concurrent requests."""
    limiter = RateLimiter(requests_per_second=5)
    
    async def make_request():
        await limiter.acquire()
        return True
    
    # Make 10 concurrent requests (2x the rate)
    tasks = [make_request() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    # All should complete
    assert len(results) == 10
    assert all(results)


@pytest.mark.asyncio
async def test_rate_limiter_throughput():
    """Test that rate limiter achieves target throughput over time."""
    target_rate = 30
    limiter = RateLimiter(requests_per_second=target_rate)
    
    # First, exhaust the initial burst capacity
    for _ in range(target_rate):
        await limiter.acquire()
    
    # Now measure sustained throughput for 1 second
    start = asyncio.get_event_loop().time()
    request_count = 0
    
    while asyncio.get_event_loop().time() - start < 1.0:
        await limiter.acquire()
        request_count += 1
    
    elapsed = asyncio.get_event_loop().time() - start
    actual_rate = request_count / elapsed
    
    # Should be close to target rate (within 20%)
    assert actual_rate >= target_rate * 0.8, f"Rate too low: {actual_rate}"
    assert actual_rate <= target_rate * 1.2, f"Rate too high: {actual_rate}"
