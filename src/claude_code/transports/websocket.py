"""
WebSocket Transport Implementation
Real-time bidirectional communication over WebSocket protocol
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.warning("websockets package not available, WebSocket transport will be simulated")

from .base import (
    Transport,
    TransportState,
    TransportMessage,
    TransportError,
    TransportConfig,
)

logger = logging.getLogger(__name__)


class WebSocketTransport(Transport):
    """
    WebSocket transport implementation

    Provides real-time bidirectional communication
    """

    def __init__(self, config: TransportConfig):
        """
        Initialize WebSocket transport

        Args:
            config: Transport configuration
        """
        super().__init__(config)

        # WebSocket connection
        self._websocket: Optional[Any] = None
        self._receive_task: Optional[asyncio.Task] = None

        # Message ordering
        self._message_sequence = 0
        self._expected_sequence = 0

    async def _connect_impl(self) -> None:
        """Establish WebSocket connection"""
        if not WEBSOCKETS_AVAILABLE:
            # Simulate connection for testing
            await asyncio.sleep(0.5)
            self._websocket = "simulated"
            logger.info("WebSocket transport connected (simulated)")
            return

        try:
            # Establish WebSocket connection
            self._websocket = await websockets.connect(
                self.config.url,
                timeout=self.config.timeout,
                ping_interval=self.config.heartbeat_interval,
                ping_timeout=self.config.timeout,
            )

            logger.info(f"WebSocket connected to {self.config.url}")

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            raise TransportError(
                f"WebSocket connection failed: {str(e)}",
                "WS_CONNECTION_ERROR"
            )

    async def _disconnect_impl(self) -> None:
        """Close WebSocket connection"""
        if self._receive_task:
            self._receive_task.cancel()

        if self._websocket and WEBSOCKETS_AVAILABLE:
            try:
                await self._websocket.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

        self._websocket = None

    async def _send_message_impl(self, message: TransportMessage) -> None:
        """
        Send message over WebSocket

        Args:
            message: Message to send
        """
        if not self._websocket:
            raise TransportError("WebSocket not connected", "WS_NOT_CONNECTED")

        try:
            # Add sequence number
            message.metadata["sequence"] = self._message_sequence
            self._message_sequence += 1

            # Convert to JSON and send
            message_json = message.to_json()

            if WEBSOCKETS_AVAILABLE and isinstance(self._websocket, object):
                await self._websocket.send(message_json)
            else:
                # Simulate sending
                await asyncio.sleep(0.01)

            logger.debug(f"WebSocket sent message {message.id} (seq {message.metadata['sequence']})")

        except Exception as e:
            raise TransportError(
                f"WebSocket send failed: {str(e)}",
                "WS_SEND_ERROR"
            )

    async def _receive_message_impl(self) -> Optional[TransportMessage]:
        """
        Receive message from WebSocket

        Returns:
            Received message or None
        """
        # This method is called by the base class, but we use our own receive loop
        # Return None to indicate no message available from this method
        return None

    async def _receive_loop(self) -> None:
        """Receive messages from WebSocket"""
        while self._running and self._websocket:
            try:
                if WEBSOCKETS_AVAILABLE and isinstance(self._websocket, object):
                    # Receive message
                    message_json = await self._websocket.recv()

                    # Parse message
                    message = TransportMessage.from_json(message_json)

                    # Check message sequence
                    sequence = message.metadata.get("sequence")
                    if sequence is not None:
                        if sequence == self._expected_sequence:
                            self._expected_sequence += 1
                        elif sequence > self._expected_sequence:
                            # Out of order message, handle appropriately
                            logger.warning(f"Received out-of-order message: {sequence} (expected {self._expected_sequence})")
                        else:
                            # Duplicate or old message, ignore
                            logger.debug(f"Ignoring old message: {sequence}")
                            continue

                    # Handle message
                    await self._handle_message(message)

                else:
                    # Simulate receiving messages
                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                await self._handle_error(TransportError(str(e), "WS_RECEIVE_ERROR"))
                break

    async def send_binary(self, data: bytes) -> None:
        """
        Send binary data over WebSocket

        Args:
            data: Binary data to send
        """
        if not self._websocket:
            raise TransportError("WebSocket not connected", "WS_NOT_CONNECTED")

        if WEBSOCKETS_AVAILABLE and isinstance(self._websocket, object):
            await self._websocket.send(data)
            self._bytes_sent += len(data)

    async def receive_binary(self) -> Optional[bytes]:
        """
        Receive binary data from WebSocket

        Returns:
            Binary data or None
        """
        if not self._websocket:
            raise TransportError("WebSocket not connected", "WS_NOT_CONNECTED")

        if WEBSOCKETS_AVAILABLE and isinstance(self._websocket, object):
            data = await self._websocket.recv()
            if isinstance(data, bytes):
                self._bytes_received += len(data)
                return data

        return None

    def get_connection_info(self) -> Dict[str, Any]:
        """Get WebSocket connection information"""
        info = {
            "type": "websocket",
            "url": self.config.url,
            "connected": self.is_connected(),
        }

        if self._websocket and WEBSOCKETS_AVAILABLE:
            info["local_address"] = self._websocket.local_address
            info["remote_address"] = self._websocket.remote_address

        return info


class WebSocketClientTransport(Transport):
    """
    WebSocket client transport for connecting to WebSocket servers
    """

    def __init__(
        self,
        url: str,
        **config_kwargs
    ):
        """
        Initialize WebSocket client transport

        Args:
            url: WebSocket server URL
            **config_kwargs: Additional configuration options
        """
        config = TransportConfig(url=url, **config_kwargs)
        super().__init__(config)

    async def _connect_impl(self) -> None:
        """Establish WebSocket client connection"""
        if not WEBSOCKETS_AVAILABLE:
            # Simulate connection for testing
            await asyncio.sleep(0.5)
            self._websocket = "simulated_client"
            logger.info(f"WebSocket client connected to {self.config.url} (simulated)")
            return

        try:
            # Establish WebSocket connection as client
            self._websocket = await websockets.connect(
                self.config.url,
                timeout=self.config.timeout,
                ping_interval=self.config.heartbeat_interval,
                ping_timeout=self.config.timeout,
            )

            logger.info(f"WebSocket client connected to {self.config.url}")

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            raise TransportError(
                f"WebSocket client connection failed: {str(e)}",
                "WS_CLIENT_CONNECTION_ERROR"
            )

    async def _disconnect_impl(self) -> None:
        """Close WebSocket client connection"""
        if self._receive_task:
            self._receive_task.cancel()

        if self._websocket and WEBSOCKETS_AVAILABLE:
            try:
                await self._websocket.close()
                logger.info("WebSocket client connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket client: {e}")

        self._websocket = None

    async def _send_message_impl(self, message: TransportMessage) -> None:
        """Send message over WebSocket client"""
        if not self._websocket:
            raise TransportError("WebSocket client not connected", "WS_CLIENT_NOT_CONNECTED")

        try:
            message_json = message.to_json()

            if WEBSOCKETS_AVAILABLE and isinstance(self._websocket, object):
                await self._websocket.send(message_json)
            else:
                await asyncio.sleep(0.01)

            logger.debug(f"WebSocket client sent message {message.id}")

        except Exception as e:
            raise TransportError(
                f"WebSocket client send failed: {str(e)}",
                "WS_CLIENT_SEND_ERROR"
            )

    async def _receive_message_impl(self) -> Optional[TransportMessage]:
        """Receive message from WebSocket client"""
        return None

    async def _receive_loop(self) -> None:
        """Receive messages from WebSocket client"""
        while self._running and self._websocket:
            try:
                if WEBSOCKETS_AVAILABLE and isinstance(self._websocket, object):
                    message_json = await self._websocket.recv()
                    message = TransportMessage.from_json(message_json)
                    await self._handle_message(message)
                else:
                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket client receive loop: {e}")
                break
