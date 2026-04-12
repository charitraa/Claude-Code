"""
MCP (Model Context Protocol) Server for Claude Code CLI
Provides tool, resource, and prompt capabilities via MCP protocol
"""

from .server import MCPServer
from .types import (
    MCPCapabilities,
    MCPTool,
    MCPResource,
    MCPPrompt,
    MCPMessage,
    MCPError,
)

__all__ = [
    "MCPServer",
    "MCPCapabilities",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    "MCPMessage",
    "MCPError",
]
