"""
REPL (Read-Eval-Print Loop) implementation using Textual
Replaces React/Ink REPL screen
"""

from typing import Optional, List
from textual.app import App, ComposeResult
from textual.widgets import (
    Input,
    Markdown,
    Static,
    ProgressBar,
)
from textual.containers import (
    Container,
    Vertical,
    Horizontal,
)
from textual.reactive import reactive
from textual import events
from textual import log

from ..state import AppState, AppStateManager
from ..config import Settings
from ..types import Message, ToolUseBlock, ToolResultContent


class MessageContainer(Static):
    """Container for displaying messages"""

    def render_message(self, message: Message) -> str:
        """
        Render a message for display

        Args:
            message: Message to render

        Returns:
            Formatted message string
        """
        # This would be expanded to handle different message types
        return f"[bold]{message.role}:[/bold] {self._format_content(message)}"

    def _format_content(self, message: Message) -> str:
        """Format message content"""
        if not message.content:
            return ""

        content_text = []
        for block in message.content:
            if hasattr(block, 'text'):
                content_text.append(block.text)
            elif hasattr(block, 'name'):  # Tool use
                content_text.append(f"Tool: {block.name}")
            elif hasattr(block, 'tool_use_id'):  # Tool result
                content_text.append(f"Tool Result: {block.tool_use_id}")

        return " ".join(content_text)


class InputPanel(Container):
    """Input panel for user messages"""

    def compose(self) -> ComposeResult:
        yield Static("Ask Claude:", id="prompt-label")
        yield Input(
            placeholder="Enter your message...",
            id="message-input",
        )


class REPLScreen(App):
    """
    Main REPL screen for Claude Code CLI

    Replaces the TypeScript REPL.tsx screen with Textual App
    """

    CSS = """
    Screen {
        layout: vertical;
    }
    #main-container {
        height: 1fr;
        overflow-y: auto;
    }
    #input-panel {
        height: 3;
        dock: bottom;
    }
    #message-container {
        height: 1fr;
    }
    #loading-indicator {
        display: none;
    }
    """

    def __init__(self, settings: Settings, app_state: AppState, console=None):
        super().__init__()
        self.settings = settings
        self.app_state = app_state
        self.console = console

        # Reactive state
        self.messages = reactive([])
        self.is_loading = reactive(False)
        self.loading_message = reactive("")

        # Subscribe to state changes
        self._setup_state_subscribers()

    def _setup_state_subscribers(self) -> None:
        """Setup subscribers to app state changes"""
        async def on_message_added(**kwargs):
            message = kwargs.get('message')
            if message:
                self.messages = self.messages + [message]

        async def on_ui_loading_changed(**kwargs):
            self.is_loading = kwargs.get('is_loading', False)
            self.loading_message = kwargs.get('message', '')

        async def on_tool_result(**kwargs):
            result = kwargs.get('result')
            if result:
                await self._handle_tool_result(result)

        # Subscribe to events
        self.app_state.subscribe("message_added", on_message_added)
        self.app_state.subscribe("ui_loading_changed", on_ui_loading_changed)
        self.app_state.subscribe("tool_result", on_tool_result)

    def compose(self) -> ComposeResult:
        """Compose the UI"""
        yield Container(
            Vertical(
                Container(id="message-container"),
                Container(id="loading-indicator"),
            ),
            id="main-container",
        )
        yield InputPanel(id="input-panel")

    def on_mount(self) -> None:
        """Called when the app is mounted"""
        # Update status to ready
        import asyncio
        asyncio.create_task(self.app_state.update_status(
            AppStateStatus.READY
        ))

    async def on_input_submitted(self, event) -> None:
        """
        Handle user input submission

        Args:
            event: Input submission event
        """
        user_input = event.value.strip()

        if not user_input:
            return

        # Create user message
        from ..types import UserMessage, TextContent
        user_message = UserMessage(
            content=[TextContent(text=user_input)]
        )

        # Add to state
        await self.app_state.add_message(user_message)

        # Process the message (placeholder for now)
        await self._process_user_message(user_input)

        # Clear input
        input_widget = self.query_one("#message-input", Input)
        if input_widget:
            input_widget.value = ""

    async def _process_user_message(self, user_input: str) -> None:
        """
        Process user message through Claude API

        Args:
            user_input: User's input message
        """
        # Set loading state
        await self.app_state.update_ui_loading(True, "Thinking...")

        try:
            # This is a placeholder - actual implementation would call Claude API
            # For now, we'll simulate a response
            await asyncio.sleep(1)

            from ..types import AssistantMessage, TextContent
            assistant_message = AssistantMessage(
                content=[TextContent(text="I received your message!")]
            )

            await self.app_state.add_message(assistant_message)

        except Exception as e:
            log.error(f"Error processing message: {e}")
            await self.app_state.add_notification({
                'type': 'error',
                'message': f'Error: {str(e)}',
            })
        finally:
            await self.app_state.update_ui_loading(False)

    async def _handle_tool_result(self, result) -> None:
        """
        Handle tool execution result

        Args:
            result: Tool execution result
        """
        # Display tool result to user
        # This would be expanded to show rich tool output
        if result.success:
            await self.app_state.add_notification({
                'type': 'success',
                'message': f'Tool {result.tool_name} executed successfully',
            })
        else:
            await self.app_state.add_notification({
                'type': 'error',
                'message': f'Tool {result.tool_name} failed: {result.error}',
            })

    def watch_messages(self, old_messages, new_messages) -> None:
        """
        React to message changes

        Args:
            old_messages: Previous messages
            new_messages: New messages
        """
        # Update the message container
        message_container = self.query_one("#message-container", Container)
        if message_container and new_messages:
            # Clear existing content
            message_container.remove_children()

            # Add new messages
            for message in new_messages[-10:]:  # Show last 10 messages
                message_widget = Static(self._format_message(message))
                message_container.mount(message_widget)

    def watch_is_loading(self, old_loading, new_loading) -> None:
        """
        React to loading state changes

        Args:
            old_loading: Previous loading state
            new_loading: New loading state
        """
        loading_indicator = self.query_one("#loading-indicator", Container)
        if loading_indicator:
            if new_loading:
                loading_indicator.display = True
                loading_indicator.mount(Static(f"{self.loading_message}"))
            else:
                loading_indicator.display = False
                loading_indicator.remove_children()

    def _format_message(self, message: Message) -> str:
        """
        Format a message for display

        Args:
            message: Message to format

        Returns:
            Formatted message string
        """
        role_color = {
            'user': 'cyan',
            'assistant': 'green',
            'system': 'yellow',
        }.get(message.role, 'white')

        content = ""
        if message.content:
            for block in message.content:
                if hasattr(block, 'text'):
                    content += block.text
                elif hasattr(block, 'name'):
                    content += f"[Tool: {block.name}]"
                elif hasattr(block, 'tool_use_id'):
                    content += f"[Tool Result]"

        return f"[{role_color}]{message.role.upper()}[/{role_color}]: {content}"