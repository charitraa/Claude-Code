"""
Complete REPL workflow for Claude Code CLI
Integrates API client, tool calling, and permission system
"""

import asyncio
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from ..types import (
    Message,
    UserMessage,
    AssistantMessage,
    TextContent,
    ToolUseBlock,
    ToolResultContent,
)
from ..services.api.claude import ClaudeAPIClient, ClaudeStreamProcessor
from ..tools import ToolRegistry, ToolExecutionFramework


class REPLWorkflow:
    """
    Complete REPL workflow integrating API and tool execution

    Replaces TypeScript main REPL logic
    """

    def __init__(
        self,
        api_client: ClaudeAPIClient,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutionFramework,
        console: Console
    ):
        """
        Initialize REPL workflow

        Args:
            api_client: Claude API client
            tool_registry: Tool registry
            tool_executor: Tool execution framework
            console: Rich console for output
        """
        self.api_client = api_client
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.console = console
        self.stream_processor = ClaudeStreamProcessor()

        # Conversation state
        self.messages: List[Message] = []
        self.current_model: str = api_client.model

        # Processing state
        self.is_processing: bool = False
        self.current_tools: List[str] = []

    async def process_user_message(self, user_input: str) -> None:
        """
        Process user message through API workflow

        Args:
            user_input: User's input message
        """
        if self.is_processing:
            self.console.print("[yellow]Already processing a message. Please wait...[/yellow]")
            return

        self.is_processing = True

        try:
            # Create user message
            user_message = UserMessage(
                content=[TextContent(text=user_input)]
            )
            self.messages.append(user_message)

            # Display user message
            self._display_message(user_message)

            # Get available tools for API
            available_tools = self.tool_registry.get_available_tools()
            tool_definitions = [tool.get_definition() for tool in available_tools]

            # Process through API
            await self._process_api_response(tool_definitions)

        except Exception as e:
            self.console.print(f"[red]Error processing message: {str(e)}[/red]")
        finally:
            self.is_processing = False

    async def _process_api_response(self, tool_definitions: List[Dict]) -> None:
        """
        Process API response with streaming and tool calls

        Args:
            tool_definitions: Available tools for the model
        """
        # Create stream
        stream = await self.api_client.create_message(
            messages=self.messages,
            tools=tool_definitions,
            stream=True
        )

        # Process streaming response
        current_content = ""
        tool_calls = []
        current_tool_use = None

        async for chunk in self.stream_processor.process_stream(stream):
            chunk_type = chunk.get("type")
            data = chunk.get("data", {})

            if chunk_type == "error":
                self.console.print(f"[red]Error: {data.get('error')}[/red]")
                return

            elif chunk_type == "content_start":
                if data.get("content_type") == "text":
                    current_content = ""
                    self.console.print("\n[green]Assistant:[/green] ", end="")

            elif chunk_type == "content_delta":
                if data.get("content"):
                    current_content += data["content"]
                    self.console.print(data["content"], end="", highlight=False)

            elif chunk_type == "content_stop":
                # Create assistant message
                assistant_message = AssistantMessage(
                    content=[TextContent(text=current_content)]
                )
                self.messages.append(assistant_message)
                self.console.print()  # New line after content

            elif chunk_type == "tool_use_start":
                # Start of tool use
                current_tool_use = data.get("tool", {})
                tool_calls.append({
                    "tool_name": current_tool_use.get("name"),
                    "input_data": current_tool_use.get("input", {}),
                })
                self._display_tool_use(current_tool_use)

            elif chunk_type == "tool_use_end":
                current_tool_use = None

            elif chunk_type == "message_stop":
                # End of message, execute tools if any
                if tool_calls:
                    await self._execute_tool_calls(tool_calls)
                break

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> None:
        """
        Execute tools that were called by the model

        Args:
            tool_calls: List of tool call specifications
        """
        if not tool_calls:
            return

        self.console.print("\n[yellow]Executing tools...[/yellow]")

        # Execute tools sequentially
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool_name")
            input_data = tool_call.get("input_data", {})

            # Execute tool with permission checking
            from ..state.app_state import AppStateStatus

            from ..types import ToolContext

            context = ToolContext(
                cwd=str(asyncio.get_event_loop().get_task_context().get('cwd', '.')),
                user_id=None,
                session_id=None,
                permissions=[],
                environment={}
            )

            result = await self.tool_executor.execute_tool(
                tool_name=tool_name,
                input_data=input_data,
                context=context
            )

            # Display tool result
            self._display_tool_result(result)

            # Add tool result to messages
            if result.success and result.result:
                tool_result_content = ToolResultContent(
                    tool_use_id=f"tool_{len(self.messages)}",
                    content=result.result.content,
                    is_error=False
                )
            else:
                tool_result_content = ToolResultContent(
                    tool_use_id=f"tool_{len(self.messages)}",
                    content=result.error or "Tool execution failed",
                    is_error=True
                )

            assistant_message = AssistantMessage(
                content=[tool_result_content]
            )
            self.messages.append(assistant_message)

    def _display_message(self, message: Message) -> None:
        """
        Display a message to the user

        Args:
            message: Message to display
        """
        if message.role == "user":
            self.console.print(f"\n[cyan]You:[/cyan] ", end="")
            for block in message.content:
                if hasattr(block, 'text'):
                    self.console.print(block.text, end="", highlight=False)
                elif hasattr(block, 'name'):
                    self.console.print(f"[Tool: {block.name}]", end="")
        elif message.role == "assistant":
            self.console.print(f"\n[green]Claude:[/green] ", end="")
            for block in message.content:
                if hasattr(block, 'text'):
                    self.console.print(block.text, end="", highlight=False)
                elif hasattr(block, 'tool_use_id'):
                    if block.is_error:
                        self.console.print(f"[red]Tool Error: {block.content}[/red]")
                    else:
                        self.console.print(f"[dim]{block.content}[/dim]")

    def _display_tool_use(self, tool_data: Dict) -> None:
        """
        Display tool use to the user

        Args:
            tool_data: Tool use data
        """
        tool_name = tool_data.get("name", "Unknown")
        tool_input = tool_data.get("input", {})

        self.console.print(f"\n[yellow]🔧 Using tool: {tool_name}[/yellow]")
        if tool_input:
            import json
            self.console.print(f"   Input: {json.dumps(tool_input, indent=2)}")

    def _display_tool_result(self, result: Any) -> None:
        """
        Display tool execution result

        Args:
            result: Tool execution result
        """
        if result.success:
            self.console.print(f"[green]✓[/green] Tool executed successfully")
            if result.execution_time_ms:
                self.console.print(f"   Execution time: {result.execution_time_ms}ms")
        else:
            self.console.print(f"[red]✗[/red] Tool execution failed")
            if result.error:
                self.console.print(f"   Error: {result.error}")
            if result.execution_time_ms:
                self.console.print(f"   Execution time: {result.execution_time_ms}ms")

    def clear_conversation(self) -> None:
        """Clear the conversation history"""
        self.messages = []
        self.console.print("\n[yellow]Conversation cleared[/yellow]")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get summary of current conversation

        Returns:
            Dictionary with conversation statistics
        """
        user_messages = [m for m in self.messages if m.role == "user"]
        assistant_messages = [m for m in self.messages if m.role == "assistant"]

        return {
            "total_messages": len(self.messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "current_model": self.current_model,
            "available_tools": len(self.tool_registry.get_available_tools()),
        }

    async def save_conversation(self, file_path: str) -> None:
        """
        Save conversation to file

        Args:
            file_path: Path to save conversation
        """
        import json
        from pathlib import Path

        conversation_data = {
            "messages": [m.model_dump() for m in self.messages],
            "model": self.current_model,
            "timestamp": asyncio.get_event_loop().time(),
        }

        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(conversation_data, f, indent=2)

        self.console.print(f"[green]✓[/green] Conversation saved to {file_path}")