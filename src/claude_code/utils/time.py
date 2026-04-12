"""
Time utilities for Claude Code CLI
"""

import time
from typing import Optional
from datetime import datetime, timedelta


def get_current_timestamp() -> float:
    """Get current Unix timestamp."""
    return time.time()


def get_current_datetime() -> datetime:
    """Get current datetime."""
    return datetime.now()


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime as string."""
    return dt.strftime(format_str)


def parse_datetime(s: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse datetime from string."""
    return datetime.strptime(s, format_str)


def get_default_timeout_ms() -> int:
    """Get default bash timeout in milliseconds."""
    return 30 * 1000  # 30 seconds


def get_max_timeout_ms() -> int:
    """Get maximum bash timeout in milliseconds."""
    return 600 * 1000  # 10 minutes


def get_timeout_seconds(timeout_ms: int) -> float:
    """Convert milliseconds to seconds."""
    return timeout_ms / 1000


def get_timeout_ms(seconds: float) -> int:
    """Convert seconds to milliseconds."""
    return int(seconds * 1000)


class Timer:
    """Simple timer for measuring elapsed time."""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_checkpoint = self.start_time
    
    def elapsed(self) -> float:
        """Get elapsed time since timer started."""
        return time.time() - self.start_time
    
    def checkpoint(self) -> float:
        """Get time since last checkpoint and reset."""
        now = time.time()
        elapsed = now - self.last_checkpoint
        self.last_checkpoint = now
        return elapsed
    
    def reset(self) -> None:
        """Reset the timer."""
        self.start_time = time.time()
        self.last_checkpoint = self.start_time
