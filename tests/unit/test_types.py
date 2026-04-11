"""
Unit tests for type system
"""

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from pydantic import ValidationError

from claude_code.types.message import (
    TextContent,
    ImageContent,
    UserMessage,
    AssistantMessage,
    MessageRole,
    ContentType,
)


class TestTextContent:
    """Test TextContent model"""

    def test_text_content_creation(self):
        """Test creating text content"""
        content = TextContent(text="Hello, world!")
        assert content.type == ContentType.TEXT
        assert content.text == "Hello, world!"

    def test_text_content_validation(self):
        """Test text content validation"""
        with pytest.raises(ValidationError):
            TextContent()  # Missing required text field


class TestImageContent:
    """Test ImageContent model"""

    def test_image_content_creation(self):
        """Test creating image content"""
        content = ImageContent(
            source={
                "type": "base64",
                "media_type": "image/png",
                "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/5+hY"
            }
        )
        assert content.type == ContentType.IMAGE
        assert content.source.media_type == "image/png"


class TestUserMessage:
    """Test UserMessage model"""

    def test_user_message_creation(self):
        """Test creating user message"""
        message = UserMessage(
            content=[TextContent(text="test message")]
        )
        assert message.role == MessageRole.USER
        assert len(message.content) == 1
        assert message.content[0].text == "test message"

    def test_user_message_with_id(self):
        """Test user message with ID"""
        message = UserMessage(
            id="msg-123",
            content=[TextContent(text="test")]
        )
        assert message.id == "msg-123"
        assert message.role == MessageRole.USER


class TestAssistantMessage:
    """Test AssistantMessage model"""

    def test_assistant_message_creation(self):
        """Test creating assistant message"""
        message = AssistantMessage(
            content=[TextContent(text="assistant response")]
        )
        assert message.role == MessageRole.ASSISTANT
        assert message.content[0].text == "assistant response"

    def test_message_content_types(self):
        """Test different content types in messages"""
        text_content = TextContent(text="text")
        message = UserMessage(content=[text_content])

        assert message.content[0] == text_content
        assert message.content[0].text == "text"