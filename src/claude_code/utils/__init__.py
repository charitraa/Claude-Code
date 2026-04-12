"""
Utilities for Claude Code CLI
"""

from .logging import setup_logging, get_logger
from .env import is_env_truthy, is_env_defined, is_env_falsy, get_env, get_env_int, get_env_bool, set_env, get_user_type, get_platform, is_ant_user
from .filesystem import get_cwd, expand_path, ensure_dir, is_file, is_dir, read_file, write_file, read_text_file, write_text_file, list_dir, get_file_size, file_exists, get_extension, get_filename, get_basename
from .format import format_size, format_duration, format_timestamp, truncate_string, json_dumps, json_loads, pluralize, format_list
from .time import get_current_timestamp, get_current_datetime, format_datetime, parse_datetime, get_default_timeout_ms, get_max_timeout_ms, get_timeout_seconds, get_timeout_ms, Timer

__all__ = [
    "setup_logging",
    "get_logger",
    "is_env_truthy",
    "is_env_defined", 
    "is_env_falsy",
    "get_env",
    "get_env_int",
    "get_env_bool",
    "set_env",
    "get_user_type",
    "get_platform",
    "is_ant_user",
    "get_cwd",
    "expand_path",
    "ensure_dir",
    "is_file",
    "is_dir",
    "read_file",
    "write_file",
    "read_text_file",
    "write_text_file",
    "list_dir",
    "get_file_size",
    "file_exists",
    "get_extension",
    "get_filename",
    "get_basename",
    "format_size",
    "format_duration",
    "format_timestamp",
    "truncate_string",
    "json_dumps",
    "json_loads",
    "pluralize",
    "format_list",
    "get_current_timestamp",
    "get_current_datetime",
    "format_datetime",
    "parse_datetime",
    "get_default_timeout_ms",
    "get_max_timeout_ms",
    "get_timeout_seconds",
    "get_timeout_ms",
    "Timer",
]