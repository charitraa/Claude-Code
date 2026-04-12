"""
SSE (Server-Sent Events) Transport Implementation
Server-sent streaming for one-way communication from server to client
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass

import aiohttp

from .base import (
    Transport,
    TransportState,
    TransportMessage,
    TransportError,
    TransportConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """SSE event"""
    id: Optional[str] = None
    event: Optional[str] = None
    data: str = ""
    retry: Optional[int] = None

    def to_format(self) -> str:
        """Convert to SSE format"""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        if self.event:
            lines.append(f"event: {self.event}")

        if self.data:
            # Multi-line data is split into multiple "data:" lines
            for line in self.data.split('\n'):
                lines.append(f"data: {line}")

        if self.retry:
            lines.append(f"retry: {self.retry}")

        return '\n'.join(lines) + '\n\n'


class SSETransport(Transport):
    """
    SSE transport implementation

    Provides server-sent streaming for real-time updates
    """

    def __init__(self, config: TransportConfig):
        """
        Initialize SSE transport

        Args:
            config: Transport configuration
        """
        super().__init__(config)

        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        self._response: Optional[aiohttp.ClientResponse] = None

        # Event processing
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._event_processor_task: Optional[asyncio.Task] = None

        # Backpressure management
        self._backpressure_threshold = 0.8
        self._is_paused = False

    async def _connect_impl(self) -> None:
        """Establish SSE connection"""
        try:
            # Create HTTP session
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )

            # Connect to SSE endpoint
            self._response = await self._session.get(
                self.config.url,
                headers={
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                }
            )

            # Check response status
            if self._response.status != 200:
                raise TransportError(
                    f"SSE connection failed with status {self._response.status}",
                    "SSE_CONNECTION_ERROR",
                    recoverable=False
                )

            # Check content type
            content_type = self._response.headers.get('Content-Type', '')
            if 'text/event-stream' not in content_type:
                logger.warning(f"Unexpected content type: {content_type}")

            logger.info(f"SSE connected to {self.config.url}")

            # Start event processor
            self._event_processor_task = asyncio.create_task(self._process_sse_events())

        except Exception as e:
            raise TransportError(
                f"SSE connection failed: {str(e)}",
                "SSE_CONNECTION_ERROR"
            )

    async def _disconnect_impl(self) -> None:
        """Close SSE connection"""
        if self._event_processor_task:
            self._event_processor_task.cancel()

        if self._response:
            try:
                self._response.close()
                logger.info("SSE connection closed")
            except Exception as e:
                logger.error(f"Error closing SSE connection: {e}")

        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.error(f"Error closing HTTP session: {e}")

        self._response = None
        self._session = None

    async def _send_message_impl(self, message: TransportMessage) -> None:
        """
        Send message (SSE is typically server-to-client only)

        Args:
            message: Message to send

        Note:
            SSE is primarily for server-to-client communication.
            This method may not be supported in all implementations.
        """
        # SSE is typically server-to-client only
        # For bidirectional communication, use WebSocket or Hybrid transport
        raise TransportError(
            "SSE transport is server-to-client only. Use WebSocket or Hybrid transport for bidirectional communication.",
            "SSE_SEND_NOT_SUPPORTED",
            recoverable=False
        )

    async def _receive_message_impl(self) -> Optional[TransportMessage]:
        """Receive message from SSE event queue"""
        try:
            event = await asyncio.wait_for(
                self._event_queue.get(),
                timeout=1.0
            )

            # Convert SSE event to transport message
            message = TransportMessage(
                type=event.event or "data",
                data={"content": event.data}
            )

            if event.id:
                message.metadata["event_id"] = event.id

            return message

        except asyncio.TimeoutError:
            return None

    async def _process_sse_events(self) -> None:
        """Process SSE events from the stream"""
        try:
            async for line in self._response.content:
                if not self._running:
                    break

                # Decode line
                line_str = line.decode('utf-8').strip()

                if not line_str:
                    # Empty line separates events
                    continue

                # Parse SSE line
                if line_str.startswith('data:'):
                    data_content = line_str[5:].strip()
                    await self._handle_sse_data(data_content)

                elif line_str.startswith('event:'):
                    event_type = line_str[6:].strip()
                    # Store event type for next data line
                    pass

                elif line_str.startswith('id:'):
                    event_id = line_str[3:].strip()
                    # Store event ID
                    pass

                elif line_str.startswith('retry:'):
                    retry_ms = int(line_str[6:].strip())
                    # Handle retry logic
                    pass

        except Exception as e:
            logger.error(f"Error processing SSE events: {e}")
            await self._handle_error(TransportError(str(e), "SSE_PROCESS_ERROR"))

    async def _handle_sse_data(self, data: str) -> None:
        """
        Handle SSE data line

        Args:
            data: Data content
        """
        try:
            # Check queue size for backpressure
            queue_size = self._event_queue.qsize()
            max_size = self._event_queue.maxsize

            if queue_size >= max_size:
                logger.warning("SSE event queue full, dropping events")
                return

            # Check backpressure
            if queue_size / max_size >= self._backpressure_threshold:
                if not self._is_paused:
                    self._is_paused = True
                    logger.warning("SSE backpressure: pausing event processing")
                    # In a real implementation, you might pause the stream here
            else:
                if self._is_paused:
                    self._is_paused = False
                    logger.info("SSE backpressure: resumed event processing")

            # Parse JSON data if possible
            try:
                data_obj = json.loads(data)

                # Create transport message
                message = TransportMessage(
                    type=data_obj.get("type", "data"),
                    data=data_obj
                )

                # Handle message
                await self._handle_message(message)

            except json.JSONDecodeError:
                # Not JSON, treat as plain text
                message = TransportMessage(
                    type="data",
                    data={"content": data}
                )
                await self._handle_message(message)

        except Exception as e:
            logger.error(f"Error handling SSE data: {e}")

    async def stream_events(self) -> AsyncIterator[SSEEvent]:
        """
        Stream SSE events as they arrive

        Yields:
            SSE events
        """
        if not self._response:
            raise TransportError("Not connected to SSE stream", "SSE_NOT_CONNECTED")

        try:
            async for line in self._response.content:
                if not self._running:
                    break

                line_str = line.decode('utf-8').strip()
                event = SSEEvent()

                if line_str.startswith('data:'):
                    event.data = line_str[5:].strip()
                elif line_str.startswith('event:'):
                    event.event = line_str[6:].strip()
                elif line_str.startswith('id:'):
                    event.id = line_str[3:].strip()
                elif line_str.startswith('retry:'):
                    event.retry = int(line_str[6:].strip())

                yield event

        except Exception as e:
            logger.error(f"Error streaming SSE events: {e}")
            raise

    def get_stream_info(self) -> Dict[str, Any]:
        """Get SSE stream information"""
        info = {
            "type": "sse",
            "url": self.config.url,
            "connected": self.is_connected(),
            "backpressure_paused": self._is_paused,
            "queue_size": self._event_queue.qsize(),
            "queue_max_size": self._event_queue.maxsize,
        }

        if self._response:
            info["response_status"] = self._response.status
            info["content_type"] = self._response.headers.get('Content-Type')

        return info


class SSEServerTransport:
    """
    SSE server transport for sending events to clients

    This is for server-side implementation of SSE
    """

    def __init__(self, session: aiohttp.ClientSession):
        """
        Initialize SSE server transport

        Args:
            session: aiohttp client session
        """
        self.session = session
        self._event_buffers: Dict[str, asyncio.Queue] = {}
        self._client_connections: Dict[str, Any] = {}

    async def handle_client(self, client_id: str, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """
        Handle SSE client connection

        Args:
            client_id: Client identifier
            request: HTTP request

        Returns:
            SSE response stream
        """
        # Create event buffer for this client
        self._event_buffers[client_id] = asyncio.Queue(maxsize=100)

        # Create SSE response
        response = aiohttp.web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )

        await response.prepare(request)

        # Store client connection
        self._client_connections[client_id] = response

        # Send initial connection event
        await self.send_event(client_id, SSEEvent(
            event="connected",
            data=f"Client {client_id} connected"
        ))

        # Stream events to client
        try:
            event_buffer = self._event_buffers[client_id]
            while True:
                event = await event_buffer.get()

                # Format event as SSE
                event_str = event.to_format()

                # Send to client
                await response.write(event_str.encode('utf-8'))
                await response.drain()

        except asyncio.CancelledError:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error streaming to client {client_id}: {e}")
        finally:
            # Cleanup
            await self.disconnect_client(client_id)

    async def send_event(self, client_id: str, event: SSEEvent) -> bool:
        """
        Send event to specific client

        Args:
            client_id: Client identifier
            event: Event to send

        Returns:
            True if sent successfully
        """
        if client_id not in self._event_buffers:
            return False

        try:
            self._event_buffers[client_id].put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning(f"Event buffer full for client {client_id}")
            return False

    async def broadcast_event(self, event: SSEEvent) -> int:
        """
        Broadcast event to all connected clients

        Args:
            event: Event to broadcast

        Returns:
            Number of clients the event was sent to
        """
        sent_count = 0

        for client_id in list(self._event_buffers.keys()):
            if await self.send_event(client_id, event):
                sent_count += 1

        return sent_count

    async def disconnect_client(self, client_id: str) -> None:
        """
        Disconnect a client

        Args:
            client_id: Client identifier
        """
        if client_id in self._event_buffers:
            del self._event_buffers[client_id]

        if client_id in self._client_connections:
            del self._client_connections[client_id]

        logger.info(f"Client {client_id} disconnected")

    def get_connected_clients(self) -> List[str]:
        """Get list of connected client IDs"""
        return list(self._event_buffers.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get SSE server statistics"""
        return {
            "connected_clients": len(self._event_buffers),
            "client_ids": list(self._event_buffers.keys()),
        }
