"""
Bridge Core Architecture
Handles bridge communication, message passing, and connection management
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
import uuid

from .types import (
    BridgeMessage,
    BridgeEvent,
    BridgeEventType,
    BridgeMessageType,
    ConnectionState,
    ConnectionInfo,
    SyncState,
    BridgeStats,
)

logger = logging.getLogger(__name__)


class BridgeCore:
    """
    Core bridge functionality

    Manages communication, message passing, and connection lifecycle
    """

    def __init__(self, server_url: str, user_id: str):
        """
        Initialize bridge core

        Args:
            server_url: Bridge server URL
            user_id: User identifier
        """
        self.server_url = server_url
        self.user_id = user_id

        # Connection state
        self.connection_info = ConnectionInfo(
            state=ConnectionState.DISCONNECTED,
            server_url=server_url,
            user_id=user_id
        )

        # Message handling
        self._message_handlers: Dict[BridgeMessageType, List[Callable]] = {}
        self._event_handlers: Dict[BridgeEventType, List[Callable]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._pending_messages: Dict[str, asyncio.Future] = {}

        # Synchronization
        self.sync_state = SyncState()

        # Statistics
        self.stats = BridgeStats()

        # Event loop
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_processor_task: Optional[asyncio.Task] = None

    async def connect(self, session_id: Optional[str] = None) -> bool:
        """
        Connect to bridge server

        Args:
            session_id: Optional session ID to join

        Returns:
            True if connected successfully
        """
        if self.connection_info.state == ConnectionState.CONNECTED:
            logger.warning("Already connected")
            return True

        try:
            # Update connection state
            self.connection_info.state = ConnectionState.CONNECTING
            await self._emit_event(BridgeEventType.CONNECTED, {
                "user_id": self.user_id,
                "session_id": session_id
            })

            # Simulate connection (in real implementation, would connect to server)
            await asyncio.sleep(0.5)  # Simulate connection delay

            # Update connection info
            self.connection_info.state = ConnectionState.CONNECTED
            self.connection_info.session_id = session_id
            self.connection_info.connected_at = datetime.now().timestamp()
            self.connection_info.last_heartbeat = datetime.now().timestamp()

            # Start background tasks
            self._running = True
            self._event_loop = asyncio.get_event_loop()
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._message_processor_task = asyncio.create_task(self._process_messages())

            # Join session if provided
            if session_id:
                await self._join_session(session_id)

            logger.info(f"Connected to bridge server: {self.server_url}")
            return True

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connection_info.state = ConnectionState.ERROR
            await self._emit_event(BridgeEventType.ERROR, {"error": str(e)})
            return False

    async def disconnect(self) -> None:
        """Disconnect from bridge server"""
        if self.connection_info.state == ConnectionState.DISCONNECTED:
            return

        logger.info("Disconnecting from bridge server")

        # Stop background tasks
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._message_processor_task:
            self._message_processor_task.cancel()

        # Update connection state
        self.connection_info.state = ConnectionState.DISCONNECTED
        self.connection_info.session_id = None

        await self._emit_event(BridgeEventType.DISCONNECTED, {
            "user_id": self.user_id
        })

    async def reconnect(self) -> bool:
        """
        Reconnect to bridge server

        Returns:
            True if reconnected successfully
        """
        if self.connection_info.state == ConnectionState.CONNECTED:
            return True

        logger.info("Reconnecting to bridge server")
        self.connection_info.retry_count += 1
        self.connection_info.state = ConnectionState.RECONNECTING

        await self._emit_event(BridgeEventType.RECONNECTING, {
            "attempt": self.connection_info.retry_count
        })

        # Attempt reconnection with exponential backoff
        delay = min(2 ** self.connection_info.retry_count, 30)
        await asyncio.sleep(delay)

        # Reconnect using previous session if available
        session_id = self.connection_info.session_id
        return await self.connect(session_id)

    async def send_message(
        self,
        message_type: BridgeMessageType,
        data: Dict[str, Any],
        recipient_id: Optional[str] = None,
        expect_response: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message through the bridge

        Args:
            message_type: Type of message to send
            data: Message data
            recipient_id: Optional recipient user ID
            expect_response: Whether to wait for response

        Returns:
            Response data if expect_response is True
        """
        if self.connection_info.state != ConnectionState.CONNECTED:
            logger.error("Not connected to bridge server")
            return None

        # Create message
        message = BridgeMessage(
            type=message_type,
            sender_id=self.user_id,
            recipient_id=recipient_id,
            session_id=self.connection_info.session_id,
            data=data
        )

        # Add to pending messages if expecting response
        future = None
        if expect_response:
            future = asyncio.Future()
            self._pending_messages[message.id] = future

        # Queue message for sending
        await self._message_queue.put(message)
        self.stats.messages_sent += 1

        # Wait for response if expected
        if future:
            try:
                response = await asyncio.wait_for(future, timeout=30.0)
                return response
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for response to {message.id}")
                return None

        return None

    def register_message_handler(
        self,
        message_type: BridgeMessageType,
        handler: Callable[[BridgeMessage], Awaitable[None]]
    ) -> None:
        """
        Register a message handler

        Args:
            message_type: Type of message to handle
            handler: Async handler function
        """
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type}")

    def register_event_handler(
        self,
        event_type: BridgeEventType,
        handler: Callable[[BridgeEvent], Awaitable[None]]
    ) -> None:
        """
        Register an event handler

        Args:
            event_type: Type of event to handle
            handler: Async handler function
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type}")

    async def _process_messages(self) -> None:
        """Process outgoing messages"""
        while self._running:
            try:
                # Get message from queue
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )

                # Send message (in real implementation, would send via transport)
                await self._send_message_impl(message)

                logger.debug(f"Sent message: {message.type.value}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _send_message_impl(self, message: BridgeMessage) -> None:
        """
        Implementation of message sending

        In real implementation, this would send via transport layer
        """
        # Placeholder for actual transport implementation
        # For now, simulate immediate delivery
        pass

    async def _receive_message(self, message_data: Dict[str, Any]) -> None:
        """
        Handle received message

        Args:
            message_data: Raw message data
        """
        try:
            # Parse message
            message = BridgeMessage.from_dict(message_data)

            # Update statistics
            self.stats.messages_received += 1

            # Handle message if we have a handler
            handlers = self._message_handlers.get(message.type, [])
            for handler in handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")

            # Check if this is a response to a pending message
            if message.id in self._pending_messages:
                future = self._pending_messages.pop(message.id)
                if not future.done():
                    future.set_result(message.data)

        except Exception as e:
            logger.error(f"Error receiving message: {e}")

    async def _emit_event(self, event_type: BridgeEventType, data: Dict[str, Any]) -> None:
        """
        Emit an event to all registered handlers

        Args:
            event_type: Type of event
            data: Event data
        """
        event = BridgeEvent(type=event_type, data=data)

        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to maintain connection"""
        while self._running:
            try:
                # Send heartbeat
                await self.send_message(
                    BridgeMessageType.HEARTBEAT,
                    {"timestamp": datetime.now().timestamp()}
                )

                # Update last heartbeat
                self.connection_info.last_heartbeat = datetime.now().timestamp()

                # Wait for next heartbeat
                await asyncio.sleep(30)  # Heartbeat every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _join_session(self, session_id: str) -> None:
        """
        Join a session

        Args:
            session_id: Session ID to join
        """
        await self.send_message(
            BridgeMessageType.JOIN_SESSION,
            {"session_id": session_id}
        )

        await self._emit_event(BridgeEventType.SESSION_JOINED, {
            "session_id": session_id
        })

    async def sync_state(self, state_data: Dict[str, Any]) -> None:
        """
        Synchronize state with bridge

        Args:
            state_data: State data to sync
        """
        self.sync_state.last_sync_timestamp = datetime.now().timestamp()

        await self.send_message(
            BridgeMessageType.SYNC_STATE,
            {
                "state": state_data,
                "timestamp": self.sync_state.last_sync_timestamp
            }
        )

        await self._emit_event(BridgeEventType.STATE_SYNC, {
            "timestamp": self.sync_state.last_sync_timestamp
        })

    async def request_state(self) -> Optional[Dict[str, Any]]:
        """
        Request current state from bridge

        Returns:
            Current state data or None
        """
        response = await self.send_message(
            BridgeMessageType.REQUEST_STATE,
            {},
            expect_response=True
        )

        return response.get("state") if response else None

    def get_connection_info(self) -> ConnectionInfo:
        """Get current connection information"""
        return self.connection_info

    def get_stats(self) -> BridgeStats:
        """Get bridge statistics"""
        return self.stats

    def is_connected(self) -> bool:
        """Check if connected to bridge"""
        return self.connection_info.state == ConnectionState.CONNECTED
