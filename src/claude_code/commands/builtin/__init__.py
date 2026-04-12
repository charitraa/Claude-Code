"""
Built-in commands for Claude Code CLI
"""

from .init import InitCommand
from .config import ConfigCommand
from .auth import AuthCommand
from .git import GitCommand
from .bridge import BridgeCommand

__all__ = [
    "InitCommand",
    "ConfigCommand",
    "AuthCommand",
    "GitCommand",
    "BridgeCommand",
]


def get_builtin_commands() -> list:
    """
    Get list of built-in command classes

    Returns:
        List of command classes
    """
    return [
        InitCommand,
        ConfigCommand,
        AuthCommand,
        GitCommand,
        BridgeCommand,
    ]
