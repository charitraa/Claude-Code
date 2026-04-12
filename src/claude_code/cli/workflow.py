"""
Complete REPL workflow for Claude Code CLI
Integrates API client, tool calling, and permission system
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from datetime import datetime
from enum import Enum

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
from ..state import AppState


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class WorkflowError(Exception):
    """Custom exception for workflow errors"""
    def __init__(self, message: str, recoverable: bool = True):
        self.message = message
        self.recoverable = recoverable
        super().__init__(message)


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

    # Workflow orchestration methods

    async def run_workflow(
        self,
        workflow_steps: List[Callable],
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Run a workflow with multiple steps and retry logic

        Args:
            workflow_steps: List of async functions to execute
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Dictionary with workflow results
        """
        results = {
            "status": WorkflowStatus.RUNNING,
            "steps_completed": 0,
            "steps_failed": 0,
            "total_steps": len(workflow_steps),
            "errors": [],
            "start_time": datetime.now(),
            "end_time": None,
        }

        for i, step in enumerate(workflow_steps):
            step_name = getattr(step, '__name__', f'step_{i}')
            retry_count = 0

            while retry_count <= max_retries:
                try:
                    # Execute pre-step hooks
                    await self._execute_hooks('pre_step', step_name)

                    # Execute the step
                    self.console.print(f"[cyan]Executing step {i+1}/{len(workflow_steps)}: {step_name}[/cyan]")
                    step_result = await step()

                    # Execute post-step hooks
                    await self._execute_hooks('post_step', step_name, step_result)

                    results["steps_completed"] += 1
                    self.console.print(f"[green]✓[/green] Step {step_name} completed")
                    break

                except Exception as e:
                    retry_count += 1
                    error_msg = f"Step {step_name} failed (attempt {retry_count}/{max_retries + 1}): {str(e)}"

                    if retry_count <= max_retries:
                        self.console.print(f"[yellow]⚠[/yellow] {error_msg}, retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        self.console.print(f"[red]✗[/red] {error_msg}")
                        results["steps_failed"] += 1
                        results["errors"].append(error_msg)

                        # Execute error hooks
                        await self._execute_hooks('on_error', step_name, e)

                        # Check if error is recoverable
                        if isinstance(e, WorkflowError) and not e.recoverable:
                            results["status"] = WorkflowStatus.FAILED
                            results["end_time"] = datetime.now()
                            return results

        # Determine final status
        if results["steps_failed"] == 0:
            results["status"] = WorkflowStatus.COMPLETED
        else:
            results["status"] = WorkflowStatus.FAILED

        results["end_time"] = datetime.now()
        return results

    async def execute_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        on_retry: Optional[Callable] = None
    ) -> Any:
        """
        Execute a function with retry logic

        Args:
            func: Async function to execute
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries
            on_retry: Optional callback called on each retry

        Returns:
            Result of the function execution

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await func()

            except Exception as e:
                last_exception = e

                if attempt < max_retries:
                    if on_retry:
                        await on_retry(attempt + 1, e)

                    self.console.print(
                        f"[yellow]Retry {attempt + 1}/{max_retries} after {retry_delay}s...[/yellow]"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

        # All retries failed
        raise WorkflowError(
            f"Failed after {max_retries + 1} attempts: {str(last_exception)}",
            recoverable=False
        )

    # Hook system

    def register_hook(self, hook_type: str, callback: Callable) -> None:
        """
        Register a hook callback

        Args:
            hook_type: Type of hook ('pre_step', 'post_step', 'on_error', 'on_complete')
            callback: Async function to call
        """
        if not hasattr(self, '_hooks'):
            self._hooks = {}

        if hook_type not in self._hooks:
            self._hooks[hook_type] = []

        self._hooks[hook_type].append(callback)

    async def _execute_hooks(self, hook_type: str, *args, **kwargs) -> None:
        """
        Execute all registered hooks of a specific type

        Args:
            hook_type: Type of hooks to execute
            *args: Positional arguments to pass to hooks
            **kwargs: Keyword arguments to pass to hooks
        """
        if not hasattr(self, '_hooks'):
            return

        hooks = self._hooks.get(hook_type, [])
        for hook in hooks:
            try:
                await hook(*args, **kwargs)
            except Exception as e:
                self.console.print(f"[red]Hook error ({hook_type}): {str(e)}[/red]")

    # Workflow state management

    def save_workflow_state(self, state: Dict[str, Any]) -> None:
        """
        Save workflow state for recovery

        Args:
            state: State dictionary to save
        """
        if not hasattr(self, '_workflow_state'):
            self._workflow_state = {}

        self._workflow_state.update(state)

    def load_workflow_state(self) -> Dict[str, Any]:
        """
        Load saved workflow state

        Returns:
            Dictionary with saved state
        """
        return getattr(self, '_workflow_state', {})

    def clear_workflow_state(self) -> None:
        """Clear saved workflow state"""
        self._workflow_state = {}

    # Workflow monitoring and metrics

    def get_workflow_metrics(self) -> Dict[str, Any]:
        """
        Get workflow execution metrics

        Returns:
            Dictionary with workflow metrics
        """
        return {
            "total_messages": len(self.messages),
            "total_tool_calls": sum(1 for m in self.messages if any(
                hasattr(block, 'name') for block in m.content
            )),
            "conversation_duration": self._get_conversation_duration(),
            "last_activity": getattr(self, '_last_activity', None),
        }

    def _get_conversation_duration(self) -> Optional[float]:
        """
        Get duration of current conversation

        Returns:
            Duration in seconds, or None if not available
        """
        if not hasattr(self, '_conversation_start'):
            return None

        return (datetime.now() - self._conversation_start).total_seconds()

    async def pause_workflow(self) -> None:
        """Pause the current workflow"""
        if hasattr(self, '_workflow_status'):
            self._workflow_status = WorkflowStatus.PAUSED
        self.console.print("[yellow]Workflow paused[/yellow]")

    async def resume_workflow(self) -> None:
        """Resume the paused workflow"""
        if hasattr(self, '_workflow_status'):
            self._workflow_status = WorkflowStatus.RUNNING
        self.console.print("[green]Workflow resumed[/green]")

    async def cancel_workflow(self) -> None:
        """Cancel the current workflow"""
        if hasattr(self, '_workflow_status'):
            self._workflow_status = WorkflowStatus.FAILED
        self.console.print("[red]Workflow cancelled[/red]")