"""
API client utilities for Claude Code CLI
"""

import asyncio
import time
from typing import Callable, TypeVar, Optional, Any
from functools import wraps

T = TypeVar('T')


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
):
    """Decorator for retrying async functions with exponential backoff."""
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        break
                    
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    
                    if "rate limit" in str(e).lower():
                        delay = max(delay, 5.0)
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    should_retry: Optional[Callable[[Exception], bool]] = None,
) -> T:
    """Retry a function with exponential backoff."""
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func() if asyncio.iscoroutinefunction(func) else func()
        except Exception as e:
            last_exception = e
            
            if should_retry and not should_retry(e):
                raise
            
            if attempt >= max_retries:
                break
            
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
    
    raise last_exception


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls: list[float] = []
    
    async def acquire(self) -> None:
        """Acquire a rate limit token."""
        now = time.time()
        
        self.calls = [t for t in self.calls if now - t < self.period]
        
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.calls.append(time.time())
    
    def reset(self) -> None:
        """Reset the rate limiter."""
        self.calls = []
