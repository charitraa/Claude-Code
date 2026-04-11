"""
Type system for Claude Code CLI
"""

from .message import (
    ContentType,
    ContentBlock,
    TextContent,
    ImageContent,
    ImageSource,
    ToolUseBlock,
    ToolResultContent,
    MessageRole,
    BaseMessage,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    Message,
    Content,
)

from .tools import (
    PermissionLevel as ToolPermissionLevel,
    ToolCategory,
    ToolInputSchema,
    ToolOutputSchema,
    ToolPermission,
    ToolDefinition,
    ToolContext,
    ToolResult,
    Tool,
    ToolRegistry,
)

from .permissions import (
    PermissionLevel,
    PermissionType,
    PermissionRule,
    PermissionDecision,
    PermissionContext,
    PermissionManager,
)

__all__ = [
    # Message types
    "ContentType",
    "ContentBlock",
    "TextContent",
    "ImageContent",
    "ImageSource",
    "ToolUseBlock",
    "ToolResultContent",
    "MessageRole",
    "BaseMessage",
    "UserMessage",
    "AssistantMessage",
    "SystemMessage",
    "Message",
    "Content",

    # Tool types
    "ToolPermissionLevel",
    "ToolCategory",
    "ToolInputSchema",
    "ToolOutputSchema",
    "ToolPermission",
    "ToolDefinition",
    "ToolContext",
    "ToolResult",
    "Tool",
    "ToolRegistry",

    # Permission types
    "PermissionLevel",
    "PermissionType",
    "PermissionRule",
    "PermissionDecision",
    "PermissionContext",
    "PermissionManager",
]