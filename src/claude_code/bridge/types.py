"""
Bridge system type definitions
Defines data structures for bridge communication
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import json


class BridgeEventType(str, Enum):
    """Bridge event types"""
    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

    # Session events
    SESSION_CREATED = "session_created"
    SESSION_JOINED = "session_joined"
    SESSION_LEFT = "session_left"
    SESSION_SYNC = "session_sync"

    # Message events
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_DELIVERED = "message_delivered"

    # State events
    STATE_UPDATED = "state_updated"
    STATE_SYNC_REQUEST = "state_sync_request"
    STATE_SYNC_RESPONSE = "state_sync_response"

    # User events
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_TYPING = "user_typing"

    # Tool events
    TOOL_INVOKED = "tool_invoked"
    TOOL_RESULT = "tool_result"


class BridgeMessageType(str, Enum):
    """Bridge message types"""
    # Client messages
    HEARTBEAT = "heartbeat"
    JOIN_SESSION = "join_session"
    LEAVE_SESSION = "leave_session"
    SEND_MESSAGE = "send_message"
    INVOKE_TOOL = "invoke_tool"
    REQUEST_STATE = "request_state"
    SYNC_STATE = "sync_state"

    # Server messages
    SESSION_UPDATE = "session_update"
    MESSAGE_BROADCAST = "message_broadcast"
    STATE_UPDATE = "state_update"
    ERROR = "error"
    ACK = "ack"


class SessionState(str, Enum):
    """Session state"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    ERROR = "error"


class UserRole(str, Enum):
    """User role in session"""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class BridgeMessage(BaseModel):
    """Bridge message structure"""
    id: str = Field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
    type: BridgeMessageType
    sender_id: str
    recipient_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BridgeMessage":
        """Create from dictionary"""
        return cls(**data)


class BridgeEvent(BaseModel):
    """Bridge event"""
    type: BridgeEventType
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    data: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data
        }


class UserPresence(BaseModel):
    """User presence information"""
    user_id: str
    user_name: str
    role: UserRole
    is_online: bool = True
    is_typing: bool = False
    last_seen: float = Field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionConfig(BaseModel):
    """Session configuration"""
    session_id: str
    name: str
    description: Optional[str] = None
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    owner_id: str
    max_participants: int = 10
    is_public: bool = False
    allow_anonymous: bool = False
    settings: Dict[str, Any] = Field(default_factory=dict)


class ConnectionState(str, Enum):
    """Connection state"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ConnectionInfo(BaseModel):
    """Connection information"""
    state: ConnectionState
    server_url: str
    session_id: Optional[str] = None
    user_id: str
    connected_at: Optional[float] = None
    last_heartbeat: Optional[float] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SyncState(BaseModel):
    """Synchronization state"""
    last_sync_timestamp: float = 0.0
    pending_messages: List[str] = Field(default_factory=list)
    synced_entities: List[str] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BridgeStats(BaseModel):
    """Bridge statistics"""
    messages_sent: int = 0
    messages_received: int = 0
    tools_invoked: int = 0
    bytes_transferred: int = 0
    uptime_seconds: float = 0.0
    errors: int = 0
    reconnections: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()
