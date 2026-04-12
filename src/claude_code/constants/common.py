"""
Common utility functions
"""

import os
from functools import lru_cache
from datetime import datetime


def get_local_iso_date() -> str:
    """Returns the LOCAL date in ISO format."""
    override = os.environ.get("CLAUDE_CODE_OVERRIDE_DATE")
    if override:
        return override
    
    now = datetime.now()
    return f"{now.year}-{now.month:02d}-{now.day:02d}"


@lru_cache(maxsize=1)
def get_session_start_date() -> str:
    """Memoized for prompt-cache stability — captures the date once at session start."""
    return get_local_iso_date()


def get_local_month_year() -> str:
    """Returns 'Month YYYY' (e.g. 'February 2026') in the user's local timezone."""
    override = os.environ.get("CLAUDE_CODE_OVERRIDE_DATE")
    if override:
        date = datetime.fromisoformat(override)
    else:
        date = datetime.now()
    
    return date.strftime("%B %Y")
