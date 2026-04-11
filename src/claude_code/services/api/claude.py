"""
Anthropic API client for Claude Code CLI
Converted from TypeScript Claude API integration
"""

import asyncio
from typing import List, Optional, AsyncIterator, Dict, Any
import anthropic
from anthropic import Anthropic, AsyncAnthropic

from ..types import Message, ToolDefinition


class ClaudeAPIClient:
    """
    Anthropic API client wrapper

    Replaces TypeScript Claude API integration
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        """
        Initialize Claude API client

        Args:
            api_key: Anthropic API key
            base_url: Optional base URL for API
            model: Default model to use
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        # Initialize async client
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url
        )

    async def create_message(
        self,
        messages: List[Message],
        max_tokens: int = 4096,
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        stream: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Create a message with streaming support

        Args:
            messages: Conversation messages
            max_tokens: Maximum tokens to generate
            tools: Available tools for the model
            temperature: Sampling temperature
            stream: Whether to stream the response

        Returns:
            AsyncIterator of response chunks
        """
        try:
            # Convert messages to API format
            api_messages = self._messages_to_api_format(messages)

            # Convert tools to API format
            api_tools = None
            if tools:
                api_tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                    for tool in tools
                ]

            # Create message with streaming
            response = await self.client.messages.create(
                model=self.model,
                messages=api_messages,
                max_tokens=max_tokens,
                tools=api_tools,
                temperature=temperature,
                stream=stream
            )

            # Stream the response
            async for chunk in response:
                yield {
                    "type": "chunk",
                    "data": chunk.model_dump()
                }

        except anthropic.AuthenticationError:
            yield {
                "type": "error",
                "error": "Authentication failed. Please check your API key.",
            }
        except anthropic.RateLimitError:
            yield {
                "type": "error",
                "error": "Rate limit exceeded. Please try again later.",
            }
        except anthropic.APIConnectionError as e:
            yield {
                "type": "error",
                "error": f"Connection error: {str(e)}",
            }
        except Exception as e:
            yield {
                "type": "error",
                "error": f"API error: {str(e)}",
            }

    def _messages_to_api_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Convert message types to API format

        Args:
            messages: List of Message objects

        Returns:
            List of API-formatted messages
        """
        api_messages = []

        for message in messages:
            api_message = {
                "role": message.role,
            }

            # Convert content blocks to API format
            api_content = []
            for block in message.content:
                if hasattr(block, 'text'):
                    api_content.append({
                        "type": "text",
                        "text": block.text,
                    })
                elif hasattr(block, 'name'):  # Tool use
                    api_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                elif hasattr(block, 'tool_use_id'):  # Tool result
                    api_content.append({
                        "type": "tool_result",
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                        "is_error": block.is_error,
                    })

            api_message["content"] = api_content

            api_messages.append(api_message)

        return api_messages


class ClaudeStreamProcessor:
    """
    Process streaming responses from Claude API

    Handles different event types (content_block_delta, content_block_stop, etc.)
    """

    def __init__(self):
        self.current_content = ""
        self.current_tool_use = None
        self.events = []

    async def process_stream(self, stream: AsyncIterator[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
        """
        Process streaming response and yield events

        Args:
            stream: Stream of API chunks

        Yields:
            Processed events
        """
        async for chunk in stream:
            chunk_type = chunk.get("type")
            data = chunk.get("data", {})

            if chunk_type == "error":
                yield {
                    "type": "error",
                    "error": data.get("error"),
                }
                break

            if chunk_type == "chunk":
                event_type = data.get("type")

                if event_type == "content_block_start":
                    # Start of new content block
                    block_type = data.get("content_block", {}).get("type")
                    if block_type == "text":
                        self.current_content = ""
                        yield {
                            "type": "content_start",
                            "content_type": "text",
                        }
                    elif block_type == "tool_use":
                        self.current_tool_use = data.get("content_block", {})
                        yield {
                            "type": "tool_use_start",
                            "tool": self.current_tool_use,
                        }

                elif event_type == "content_block_delta":
                    # Delta for current content block
                    delta_type = data.get("delta", {}).get("type")
                    delta = data.get("delta", {}).get("text", "")

                    if delta_type == "text_delta" and delta:
                        self.current_content += delta
                        yield {
                            "type": "content_delta",
                            "content": delta,
                        }

                elif event_type == "content_block_stop":
                    # End of current content block
                    yield {
                        "type": "content_stop",
                        "content": self.current_content,
                    }
                    self.current_content = ""

                elif event_type == "message_stop":
                    # End of message
                    yield {
                        "type": "message_stop",
                    }
                    break