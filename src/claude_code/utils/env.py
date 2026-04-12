"""
Environment utilities for Claude Code CLI
"""

import os
from typing import Optional, Any


def is_env_truthy(value: Optional[str]) -> bool:
    """Check if environment variable is truthy."""
    if value is None:
        return False
    return value.lower() in ("true", "1", "yes")


def is_env_defined(value: Optional[str]) -> bool:
    """Check if environment variable is defined and non-empty."""
    return value is not None and value != ""


def is_env_falsy(value: Optional[str]) -> bool:
    """Check if environment variable is falsy or not set."""
    if value is None:
        return True
    return value.lower() in ("false", "0", "no", "")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default."""
    return os.environ.get(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """Get environment variable as integer."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    value = os.environ.get(key)
    if value is None:
        return default
    return is_env_truthy(value)


def set_env(key: str, value: str) -> None:
    """Set environment variable."""
    os.environ[key] = value


def get_user_type() -> str:
    """Get USER_TYPE environment variable."""
    return os.environ.get("USER_TYPE", "")


def get_platform() -> str:
    """Get platform (darwin, linux, win32)."""
    return os.environ.get("PLATFORM", os.sys.platform)


def is_ant_user() -> bool:
    """Check if running as ant user."""
    return get_user_type() == "ant"
