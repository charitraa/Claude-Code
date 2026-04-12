"""
Base Transport Interface
Abstract transport protocol for bridge communication
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Callable, Awaitable
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


class TransportState(str, Enum):
    """Transport connection state"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    CLOSING = "closing"


class TransportError(Exception):
    """Transport-specific error"""

    def __init__(self, message: str, code: Optional[str] = None, recoverable: bool = True):
        self.message = message
        self.code = code
        self.recoverable = recoverable
        super().__init__(message)


@dataclass
class TransportMessage:
    """Transport message wrapper"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "data"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        })

    @classmethod
    def from_json(cls, json_str: str) -> "TransportMessage":
        """Create message from JSON string"""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class TransportConfig:
    """Transport configuration"""
    url: str
    timeout: float = 30.0
    reconnect_interval: float = 5.0
    max_reconnect_attempts: int = 10
    heartbeat_interval: float = 30.0
    message_queue_size: int = 1000
    compression: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class Transport(ABC):
    """
    Abstract base class for transport implementations

    All transport implementations must inherit from this class
    """

    def __init__(self, config: TransportConfig):
        """
        Initialize transport

        Args:
            config: Transport configuration
        """
        self.config = config
        self.state = TransportState.DISCONNECTED

        # Message handling
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=config.message_queue_size)
        self._pending_messages: Dict[str, asyncio.Future] = {}

        # Event handlers
        self._message_handlers: List[Callable[[TransportMessage], Awaitable[None]]] = []
        self._state_handlers: List[Callable[[TransportState], Awaitable[None]]] = []
        self._error_handlers: List[Callable[[TransportError], Awaitable[None]]] = []

        # Connection management
        self._connection_lock = asyncio.Lock()
        self._reconnect_attempts = 0
        self._last_error: Optional[TransportError] = None

        # Background tasks
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_processor_task: Optional[asyncio.Task] = None

        # Statistics
        self._messages_sent = 0
        self._messages_received = 0
        self._bytes_sent = 0
        self._bytes_received = 0
        self._connection_start_time: Optional[float] = None

    @abstractmethod
    async def _connect_impl(self) -> None:
        """
        Implementation-specific connection logic

        Must be implemented by subclasses
        """
        pass

    @abstractmethod
    async def _disconnect_impl(self) -> None:
        """
        Implementation-specific disconnection logic

        Must be implemented by subclasses
        """
        pass

    @abstractmethod
    async def _send_message_impl(self, message: TransportMessage) -> None:
        """
        Implementation-specific message sending logic

        Must be implemented by subclasses

        Args:
            message: Message to send
        """
        pass

    @abstractmethod
    async def _receive_message_impl(self) -> Optional[TransportMessage]:
        """
        Implementation-specific message receiving logic

        Must be implemented by subclasses

        Returns:
            Received message or None if no message
        """
        pass

    async def connect(self) -> bool:
        """
        Connect to the transport endpoint

        Returns:
            True if connected successfully
        """
        async with self._connection_lock:
            if self.state in [TransportState.CONNECTED, TransportState.CONNECTING]:
                logger.warning(f"Already {self.state.value}")
                return True

            try:
                self.state = TransportState.CONNECTING
                await self._emit_state_change(TransportState.CONNECTING)

                # Call implementation-specific connect
                await self._connect_impl()

                # Update state
                self.state = TransportState.CONNECTED
                self._connection_start_time = datetime.now().timestamp()
                self._reconnect_attempts = 0
                self._last_error = None

                # Start background tasks
                self._running = True
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self._message_processor_task = asyncio.create_task(self._process_messages())

                await self._emit_state_change(TransportState.CONNECTED)
                logger.info(f"Transport connected: {self.config.url}")

                return True

            except Exception as e:
                error = TransportError(f"Connection failed: {str(e)}", "CONNECTION_ERROR")
                await self._handle_error(error)
                return False

    async def disconnect(self) -> None:
        """Disconnect from the transport endpoint"""
        async with self._connection_lock:
            if self.state == TransportState.DISCONNECTED:
                return

            try:
                self.state = TransportState.CLOSING
                await self._emit_state_change(TransportState.CLOSING)

                # Stop background tasks
                self._running = False
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                if self._message_processor_task:
                    self._message_processor_task.cancel()

                # Call implementation-specific disconnect
                await self._disconnect_impl()

                # Update state
                self.state = TransportState.DISCONNECTED
                self._connection_start_time = None

                await self._emit_state_change(TransportState.DISCONNECTED)
                logger.info("Transport disconnected")

            except Exception as e:
                error = TransportError(f"Disconnect failed: {str(e)}", "DISCONNECT_ERROR")
                await self._handle_error(error)

    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the transport endpoint

        Returns:
            True if reconnected successfully
        """
        if self.state == TransportState.CONNECTED:
            return True

        if self._reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return False

        self._reconnect_attempts += 1
        self.state = TransportState.RECONNECTING
        await self._emit_state_change(TransportState.RECONNECTING)

        # Wait before reconnecting
        await asyncio.sleep(self.config.reconnect_interval * self._reconnect_attempts)

        # Attempt connection
        return await self.connect()

    async def send_message(
        self,
        message: TransportMessage,
        expect_response: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message through the transport

        Args:
            message: Message to send
            expect_response: Whether to wait for response

        Returns:
            Response data if expect_response is True
        """
        if self.state != TransportState.CONNECTED:
            raise TransportError("Not connected", "NOT_CONNECTED")

        # Add to pending if expecting response
        future = None
        if expect_response:
            future = asyncio.Future()
            self._pending_messages[message.id] = future

        try:
            # Queue message for sending
            await self._message_queue.put(message)

            # Wait for response if expected
            if future:
                try:
                    response = await asyncio.wait_for(future, timeout=self.config.timeout)
                    return response
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for response to {message.id}")
                    if message.id in self._pending_messages:
                        del self._pending_messages[message.id]
                    return None

        except Exception as e:
            error = TransportError(f"Send failed: {str(e)}", "SEND_ERROR")
            await self._handle_error(error)
            raise

        return None

    async def _process_messages(self) -> None:
        """Process outgoing messages from the queue"""
        while self._running:
            try:
                # Get message from queue
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )

                # Send message
                await self._send_message_impl(message)
                self._messages_sent += 1
                self._bytes_sent += len(message.to_json())

                logger.debug(f"Sent message: {message.id}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await self._handle_error(TransportError(str(e), "MESSAGE_PROCESS_ERROR"))

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats"""
        while self._running:
            try:
                # Create heartbeat message
                heartbeat = TransportMessage(
                    type="heartbeat",
                    data={"timestamp": datetime.now().timestamp()}
                )

                await self.send_message(heartbeat)

                # Wait for next heartbeat
                await asyncio.sleep(self.config.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _receive_loop(self) -> None:
        """Receive and process incoming messages"""
        while self._running:
            try:
                # Receive message
                message = await self._receive_message_impl()

                if message:
                    # Update statistics
                    self._messages_received += 1
                    self._bytes_received += len(message.to_json())

                    # Handle message
                    await self._handle_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await self._handle_error(TransportError(str(e), "RECEIVE_ERROR"))

    async def _handle_message(self, message: TransportMessage) -> None:
        """
        Handle a received message

        Args:
            message: Message to handle
        """
        # Check if this is a response to a pending message
        if message.id in self._pending_messages:
            future = self._pending_messages.pop(message.id)
            if not future.done():
                future.set_result(message.data)
            return

        # Call registered message handlers
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    async def _handle_error(self, error: TransportError) -> None:
        """
        Handle a transport error

        Args:
            error: Error to handle
        """
        self._last_error = error
        self.state = TransportState.ERROR
        await self._emit_state_change(TransportState.ERROR)

        # Call error handlers
        for handler in self._error_handlers:
            try:
                await handler(error)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")

        # Attempt reconnection if recoverable
        if error.recoverable and self._running:
            logger.info("Attempting reconnection after error")
            await self.reconnect()

    async def _emit_state_change(self, new_state: TransportState) -> None:
        """
        Emit a state change event

        Args:
            new_state: New state
        """
        for handler in self._state_handlers:
            try:
                await handler(new_state)
            except Exception as e:
                logger.error(f"Error in state handler: {e}")

    def register_message_handler(self, handler: Callable[[TransportMessage], Awaitable[None]]) -> None:
        """Register a message handler"""
        self._message_handlers.append(handler)

    def register_state_handler(self, handler: Callable[[TransportState], Awaitable[None]]) -> None:
        """Register a state change handler"""
        self._state_handlers.append(handler)

    def register_error_handler(self, handler: Callable[[TransportError], Awaitable[None]]) -> None:
        """Register an error handler"""
        self._error_handlers.append(handler)

    def get_state(self) -> TransportState:
        """Get current transport state"""
        return self.state

    def is_connected(self) -> bool:
        """Check if transport is connected"""
        return self.state == TransportState.CONNECTED

    def get_stats(self) -> Dict[str, Any]:
        """Get transport statistics"""
        uptime = 0.0
        if self._connection_start_time:
            uptime = datetime.now().timestamp() - self._connection_start_time

        return {
            "state": self.state.value,
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
            "bytes_sent": self._bytes_sent,
            "bytes_received": self._bytes_received,
            "uptime_seconds": uptime,
            "reconnect_attempts": self._reconnect_attempts,
            "last_error": str(self._last_error) if self._last_error else None,
        }
