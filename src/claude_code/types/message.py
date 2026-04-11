"""
Message types for Claude Code CLI
Converted from TypeScript message types
"""

from typing import List, Optional, Union, Literal, Any
from pydantic import BaseModel, Field
from enum import Enum


class ContentType(str, Enum):
    """Content block types"""
    TEXT = "text"
    IMAGE = "image"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class ContentBlock(BaseModel):
    """Base content block"""
    type: ContentType


class TextContent(ContentBlock):
    """Text content block"""
    type: Literal[ContentType.TEXT] = ContentType.TEXT
    text: str


class ImageContent(ContentBlock):
    """Image content block"""
    type: Literal[ContentType.IMAGE] = ContentType.IMAGE
    source: 'ImageSource'


class ImageSource(BaseModel):
    """Image source"""
    type: Literal["base64"] = "base64"
    media_type: str = Field(..., description="MIME type of the image")
    data: str = Field(..., description="Base64 encoded image data")


class ToolUseBlock(ContentBlock):
    """Tool use content block"""
    type: Literal[ContentType.TOOL_USE] = ContentType.TOOL_USE
    id: str = Field(..., description="Unique identifier for this tool use")
    name: str = Field(..., description="Name of the tool to use")
    input: dict = Field(default_factory=dict, description="Input parameters for the tool")


class ToolResultContent(ContentBlock):
    """Tool result content block"""
    type: Literal[ContentType.TOOL_RESULT] = ContentType.TOOL_RESULT
    tool_use_id: str = Field(..., description="ID of the tool use this result corresponds to")
    content: Union[str, List[ContentBlock]] = Field(..., description="Result content")
    is_error: bool = Field(default=False, description="Whether the tool execution resulted in an error")


class MessageRole(str, Enum):
    """Message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class BaseMessage(BaseModel):
    """Base message class"""
    role: MessageRole
    content: List[ContentBlock]
    id: Optional[str] = None


class UserMessage(BaseMessage):
    """User message"""
    role: Literal[MessageRole.USER] = MessageRole.USER


class AssistantMessage(BaseMessage):
    """Assistant message"""
    role: Literal[MessageRole.ASSISTANT] = MessageRole.ASSISTANT


class SystemMessage(BaseMessage):
    """System message"""
    role: Literal[MessageRole.SYSTEM] = MessageRole.SYSTEM


# Type aliases for convenience
Message = Union[UserMessage, AssistantMessage, SystemMessage]
Content = Union[TextContent, ImageContent, ToolUseBlock, ToolResultContent]