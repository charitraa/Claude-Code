"""
Bridge System for Claude Code CLI
Enables remote sessions and collaborative features
"""

from .core import BridgeCore, BridgeMessage, BridgeEventType
from .session import BridgeSession, SessionState, SessionManager
from .auth import BridgeAuth, AuthToken, DeviceInfo

__all__ = [
    "BridgeCore",
    "BridgeMessage",
    "BridgeEventType",
    "BridgeSession",
    "SessionState",
    "SessionManager",
    "BridgeAuth",
    "AuthToken",
    "DeviceInfo",
]
