"""
Format utilities for Claude Code CLI
"""

from typing import Any
import json


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp as ISO string."""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).isoformat()


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to max length."""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def json_dumps(obj: Any, pretty: bool = False) -> str:
    """Serialize object to JSON."""
    if pretty:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    return json.dumps(obj, ensure_ascii=False)


def json_loads(s: str) -> Any:
    """Deserialize JSON string to object."""
    return json.loads(s)


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """Return singular or plural form based on count."""
    if count == 1:
        return singular
    return plural if plural else f"{singular}s"


def format_list(items: list[str], conjunction: str = "and") -> str:
    """Format list as grammatical string."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    return ", ".join(items[:-1]) + f", {conjunction} {items[-1]}"
