"""
Utility functions for Claude Code CLI
"""

import os
from pathlib import Path
from typing import Optional


def get_cwd() -> str:
    """Get current working directory."""
    return os.getcwd()


def expand_path(path: str) -> Path:
    """Expand user home directory and resolve path."""
    return Path(os.path.expanduser(path)).resolve()


def ensure_dir(path: str) -> None:
    """Ensure a directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)


def is_file(path: str) -> bool:
    """Check if path is a file."""
    return Path(path).is_file()


def is_dir(path: str) -> bool:
    """Check if path is a directory."""
    return Path(path).is_dir()


def read_file(path: str) -> bytes:
    """Read file as bytes."""
    return Path(path).read_bytes()


def write_file(path: str, content: bytes) -> None:
    """Write bytes to file."""
    Path(path).write_bytes(content)


def read_text_file(path: str) -> str:
    """Read file as text."""
    return Path(path).read_text()


def write_text_file(path: str, content: str) -> None:
    """Write text to file."""
    Path(path).write_text(content)


def list_dir(path: str) -> list[str]:
    """List directory contents."""
    return [str(p.name) for p in Path(path).iterdir()]


def get_file_size(path: str) -> int:
    """Get file size in bytes."""
    return Path(path).stat().st_size


def file_exists(path: str) -> bool:
    """Check if file exists."""
    return Path(path).exists()


def get_extension(path: str) -> str:
    """Get file extension."""
    return Path(path).suffix


def get_filename(path: str) -> str:
    """Get filename without extension."""
    return Path(path).stem


def get_basename(path: str) -> str:
    """Get basename of path."""
    return Path(path).name
