"""
State management system for Claude Code CLI
Replaces React contexts and state management
"""

import asyncio
from typing import List, Dict, Optional, Callable, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

from ..types import Message, ToolResult
from ..config import Settings


class AppStateStatus(str, Enum):
    """Application state status"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class ConversationState(BaseModel):
    """Conversation state"""
    messages: List[Message] = Field(default_factory=list)
    current_message_index: int = 0
    total_tokens_used: int = 0
    model: str = "claude-sonnet-4-20250514"


class TaskState(BaseModel):
    """Task state for task management"""
    current_task_id: Optional[str] = None
    active_tasks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    completed_tasks: List[str] = Field(default_factory=list)


class UIState(BaseModel):
    """UI state"""
    current_screen: str = "repl"
    is_loading: bool = False
    loading_message: Optional[str] = None
    notifications: List[Dict[str, Any]] = Field(default_factory=list)


class AppState:
    """
    Central application state management

    Replaces React's AppStateProvider and context system
    Uses pub/sub pattern for state updates
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()

        # Core state
        self.status = AppStateStatus.INITIALIZING
        self.conversation = ConversationState()
        self.tasks = TaskState()
        self.ui = UIState()

        # Event subscribers
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()

        # Lock for thread-safe updates
        self._lock = asyncio.Lock()

    def subscribe(self, event: str, callback: Callable) -> None:
        """
        Subscribe to state change events

        Args:
            event: Event name to subscribe to
            callback: Function to call when event occurs
        """
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        """
        Unsubscribe from state change events

        Args:
            event: Event name to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event in self._subscribers:
            try:
                self._subscribers[event].remove(callback)
            except ValueError:
                pass

    async def publish(self, event: str, **kwargs) -> None:
        """
        Publish a state change event

        Args:
            event: Event name
            **kwargs: Event data
        """
        await self._event_queue.put((event, kwargs))

    async def _process_events(self) -> None:
        """Process events from the queue"""
        while True:
            event, kwargs = await self._event_queue.get()

            # Notify all subscribers
            if event in self._subscribers:
                for callback in self._subscribers[event]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(**kwargs)
                        else:
                            callback(**kwargs)
                    except Exception as e:
                        print(f"Error in event handler for {event}: {e}")

    async def start_event_loop(self) -> None:
        """Start the event processing loop"""
        await self._process_events()

    # State update methods

    async def update_status(self, status: AppStateStatus) -> None:
        """
        Update application status

        Args:
            status: New status
        """
        self.status = status
        await self.publish("status_change", status=status)

    async def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation

        Args:
            message: Message to add
        """
        async with self._lock:
            self.conversation.messages.append(message)
        await self.publish("message_added", message=message)

    async def add_messages(self, messages: List[Message]) -> None:
        """
        Add multiple messages to the conversation

        Args:
            messages: Messages to add
        """
        async with self._lock:
            self.conversation.messages.extend(messages)
        await self.publish("messages_added", messages=messages)

    async def clear_messages(self) -> None:
        """Clear all messages from conversation"""
        async with self._lock:
            self.conversation.messages = []
        await self.publish("messages_cleared")

    async def update_ui_loading(self, is_loading: bool, message: Optional[str] = None) -> None:
        """
        Update UI loading state

        Args:
            is_loading: Whether UI is loading
            message: Optional loading message
        """
        self.ui.is_loading = is_loading
        self.ui.loading_message = message
        await self.publish("ui_loading_changed", is_loading=is_loading, message=message)

    async def add_notification(self, notification: Dict[str, Any]) -> None:
        """
        Add a notification to UI

        Args:
            notification: Notification data
        """
        self.ui.notifications.append(notification)
        await self.publish("notification_added", notification=notification)

    async def add_tool_result(self, result: ToolResult) -> None:
        """
        Add a tool result to state

        Args:
            result: Tool execution result
        """
        await self.publish("tool_result", result=result)

    def get_messages(self) -> List[Message]:
        """
        Get all messages from conversation

        Returns:
            List of messages
        """
        return self.conversation.messages.copy()

    def get_last_message(self) -> Optional[Message]:
        """
        Get the last message from conversation

        Returns:
            Last message, or None if no messages
        """
        if self.conversation.messages:
            return self.conversation.messages[-1]
        return None

    async def reset(self) -> None:
        """Reset application state to initial values"""
        self.conversation = ConversationState()
        self.tasks = TaskState()
        self.ui = UIState()
        self.status = AppStateStatus.READY

        await self.publish("state_reset")


class AppStateManager:
    """
    Global application state manager

    Singleton pattern for managing global app state
    """

    _instance: Optional[AppState] = None

    @classmethod
    def get_instance(cls, settings: Optional[Settings] = None) -> AppState:
        """
        Get the global AppState instance

        Args:
            settings: Optional settings for initialization

        Returns:
            Global AppState instance
        """
        if cls._instance is None:
            cls._instance = AppState(settings)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the global AppState instance"""
        cls._instance = None