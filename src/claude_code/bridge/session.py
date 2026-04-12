"""
Bridge Session Management
Handles session creation, lifecycle, and synchronization
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path
import uuid

from .types import (
    SessionConfig,
    SessionState,
    UserPresence,
    UserRole,
    BridgeEvent,
    BridgeEventType,
)

logger = logging.getLogger(__name__)


class BridgeSession:
    """
    Represents a single bridge session
    """

    def __init__(self, config: SessionConfig):
        """
        Initialize bridge session

        Args:
            config: Session configuration
        """
        self.config = config
        self.state = SessionState.INITIALIZING

        # Participants
        self.participants: Dict[str, UserPresence] = {}
        self.owner_id = config.owner_id

        # Session data
        self.messages: List[Dict[str, Any]] = []
        self.shared_state: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

        # Timestamps
        self.created_at = config.created_at
        self.last_activity = datetime.now().timestamp()

        # Event handlers
        self._event_handlers: List[Callable] = []

    def add_participant(
        self,
        user_id: str,
        user_name: str,
        role: UserRole = UserRole.VIEWER
    ) -> UserPresence:
        """
        Add a participant to the session

        Args:
            user_id: User identifier
            user_name: User name
            role: User role

        Returns:
            UserPresence instance
        """
        presence = UserPresence(
            user_id=user_id,
            user_name=user_name,
            role=role,
            is_online=True
        )

        self.participants[user_id] = presence
        self.last_activity = datetime.now().timestamp()

        # Emit event
        self._emit_event("participant_joined", {
            "user_id": user_id,
            "user_name": user_name,
            "role": role.value
        })

        logger.info(f"Participant added to session: {user_name} ({user_id})")
        return presence

    def remove_participant(self, user_id: str) -> bool:
        """
        Remove a participant from the session

        Args:
            user_id: User identifier

        Returns:
            True if removed, False if not found
        """
        if user_id in self.participants:
            del self.participants[user_id]
            self.last_activity = datetime.now().timestamp()

            # Emit event
            self._emit_event("participant_left", {"user_id": user_id})

            logger.info(f"Participant removed from session: {user_id}")
            return True

        return False

    def update_participant_presence(
        self,
        user_id: str,
        is_online: Optional[bool] = None,
        is_typing: Optional[bool] = None
    ) -> bool:
        """
        Update participant presence

        Args:
            user_id: User identifier
            is_online: Online status
            is_typing: Typing status

        Returns:
            True if updated, False if not found
        """
        participant = self.participants.get(user_id)
        if not participant:
            return False

        if is_online is not None:
            participant.is_online = is_online

        if is_typing is not None:
            participant.is_typing = is_typing

        participant.last_seen = datetime.now().timestamp()
        self.last_activity = datetime.now().timestamp()

        return True

    def add_message(self, message: Dict[str, Any]) -> None:
        """
        Add a message to the session

        Args:
            message: Message data
        """
        self.messages.append(message)
        self.last_activity = datetime.now().timestamp()

        # Emit event
        self._emit_event("message_added", {
            "message_id": message.get("id"),
            "sender_id": message.get("sender_id")
        })

    def update_state(self, state_data: Dict[str, Any]) -> None:
        """
        Update shared session state

        Args:
            state_data: State data to update
        """
        self.shared_state.update(state_data)
        self.last_activity = datetime.now().timestamp()

        # Emit event
        self._emit_event("state_updated", {
            "keys": list(state_data.keys())
        })

    def get_participant(self, user_id: str) -> Optional[UserPresence]:
        """Get participant information"""
        return self.participants.get(user_id)

    def get_participants(self, role: Optional[UserRole] = None) -> List[UserPresence]:
        """
        Get participants, optionally filtered by role

        Args:
            role: Optional role filter

        Returns:
            List of UserPresence
        """
        participants = list(self.participants.values())

        if role:
            participants = [p for p in participants if p.role == role]

        return participants

    def is_participant(self, user_id: str) -> bool:
        """Check if user is a participant"""
        return user_id in self.participants

    def set_state(self, state: SessionState) -> None:
        """Set session state"""
        self.state = state
        self._emit_event("state_changed", {"state": state.value})

    def register_event_handler(self, handler: Callable) -> None:
        """Register an event handler"""
        self._event_handlers.append(handler)

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit session event"""
        for handler in self._event_handlers:
            try:
                handler(event_type, data)
            except Exception as e:
                logger.error(f"Error in session event handler: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "config": self.config.model_dump(),
            "state": self.state.value,
            "participants": {
                user_id: presence.to_dict()
                for user_id, presence in self.participants.items()
            },
            "message_count": len(self.messages),
            "shared_state": self.shared_state,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "metadata": self.metadata
        }


class SessionManager:
    """
    Manages multiple bridge sessions
    """

    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Initialize session manager

        Args:
            sessions_dir: Directory to store session data
        """
        self.sessions_dir = sessions_dir or (Path.home() / ".claude" / "bridge" / "sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Active sessions
        self._sessions: Dict[str, BridgeSession] = {}
        self._user_sessions: Dict[str, str] = {}  # user_id -> session_id

        # Event handlers
        self._event_handlers: List[Callable] = []

        # Load persisted sessions
        self._load_sessions()

    def create_session(
        self,
        name: str,
        owner_id: str,
        description: Optional[str] = None,
        max_participants: int = 10,
        is_public: bool = False,
        settings: Optional[Dict[str, Any]] = None
    ) -> BridgeSession:
        """
        Create a new session

        Args:
            name: Session name
            owner_id: Owner user ID
            description: Session description
            max_participants: Maximum number of participants
            is_public: Whether session is public
            settings: Additional session settings

        Returns:
            BridgeSession instance
        """
        session_id = str(uuid.uuid4())

        config = SessionConfig(
            session_id=session_id,
            name=name,
            description=description,
            owner_id=owner_id,
            max_participants=max_participants,
            is_public=is_public,
            settings=settings or {}
        )

        session = BridgeSession(config)

        # Add owner as participant
        session.add_participant(owner_id, "Owner", UserRole.OWNER)

        # Store session
        self._sessions[session_id] = session
        self._user_sessions[owner_id] = session_id

        # Save session
        self._save_session(session)

        # Emit event
        self._emit_event("session_created", {
            "session_id": session_id,
            "name": name,
            "owner_id": owner_id
        })

        logger.info(f"Session created: {name} ({session_id})")
        return session

    def get_session(self, session_id: str) -> Optional[BridgeSession]:
        """Get a session by ID"""
        return self._sessions.get(session_id)

    def get_user_session(self, user_id: str) -> Optional[BridgeSession]:
        """Get the session a user is in"""
        session_id = self._user_sessions.get(user_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def join_session(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
        role: UserRole = UserRole.VIEWER
    ) -> Optional[BridgeSession]:
        """
        Join a session

        Args:
            session_id: Session ID to join
            user_id: User ID
            user_name: User name
            role: User role

        Returns:
            BridgeSession if joined successfully, None otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return None

        # Check if session is full
        if len(session.participants) >= session.config.max_participants:
            logger.warning(f"Session is full: {session_id}")
            return None

        # Add user to session
        session.add_participant(user_id, user_name, role)
        self._user_sessions[user_id] = session_id

        # Save session
        self._save_session(session)

        logger.info(f"User joined session: {user_name} -> {session_id}")
        return session

    def leave_session(self, user_id: str) -> bool:
        """
        Leave current session

        Args:
            user_id: User ID

        Returns:
            True if left successfully, False otherwise
        """
        session_id = self._user_sessions.get(user_id)
        if not session_id:
            return False

        session = self.get_session(session_id)
        if not session:
            del self._user_sessions[user_id]
            return False

        # Remove participant
        session.remove_participant(user_id)
        del self._user_sessions[user_id]

        # Save session
        self._save_session(session)

        # Check if session should be terminated
        if len(session.participants) == 0:
            self.terminate_session(session_id)

        logger.info(f"User left session: {user_id} <- {session_id}")
        return True

    def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a session

        Args:
            session_id: Session ID to terminate

        Returns:
            True if terminated, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Remove all participants
        for user_id in list(session.participants.keys()):
            if user_id in self._user_sessions:
                del self._user_sessions[user_id]

        # Remove session
        del self._sessions[session_id]

        # Remove persisted session
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        # Emit event
        self._emit_event("session_terminated", {
            "session_id": session_id
        })

        logger.info(f"Session terminated: {session_id}")
        return True

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        include_public: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List sessions

        Args:
            user_id: Optional user ID to filter by
            include_public: Include public sessions

        Returns:
            List of session information
        """
        sessions = []

        for session_id, session in self._sessions.items():
            # Filter by user
            if user_id and not session.is_participant(user_id):
                # Check if public and include_public is True
                if not (include_public and session.config.is_public):
                    continue

            session_info = {
                "session_id": session_id,
                "name": session.config.name,
                "description": session.config.description,
                "state": session.state.value,
                "participant_count": len(session.participants),
                "max_participants": session.config.max_participants,
                "is_public": session.config.is_public,
                "is_participant": session.is_participant(user_id) if user_id else False,
                "created_at": session.created_at,
            }

            sessions.append(session_info)

        return sessions

    def sync_session_state(
        self,
        session_id: str,
        state_data: Dict[str, Any]
    ) -> bool:
        """
        Synchronize session state

        Args:
            session_id: Session ID
            state_data: State data to sync

        Returns:
            True if synced successfully, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.update_state(state_data)
        self._save_session(session)

        return True

    def register_event_handler(self, handler: Callable) -> None:
        """Register a session manager event handler"""
        self._event_handlers.append(handler)

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit session manager event"""
        for handler in self._event_handlers:
            try:
                handler(event_type, data)
            except Exception as e:
                logger.error(f"Error in session manager event handler: {e}")

    def _save_session(self, session: BridgeSession) -> None:
        """Save session to disk"""
        session_file = self.sessions_dir / f"{session.config.session_id}.json"

        try:
            with open(session_file, 'w') as f:
                json.dump(session.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def _load_sessions(self) -> None:
        """Load sessions from disk"""
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)

                # Recreate session
                config = SessionConfig(**data["config"])
                session = BridgeSession(config)
                session.state = SessionState(data["state"])
                session.shared_state = data.get("shared_state", {})
                session.metadata = data.get("metadata", {})
                session.last_activity = data.get("last_activity", datetime.now().timestamp())

                # Restore participants
                for user_id, presence_data in data.get("participants", {}).items():
                    presence = UserPresence(**presence_data)
                    session.participants[user_id] = presence
                    self._user_sessions[user_id] = config.session_id

                self._sessions[config.session_id] = session
                logger.debug(f"Loaded session: {config.name}")

            except Exception as e:
                logger.error(f"Error loading session from {session_file}: {e}")

    def cleanup_inactive_sessions(self, max_inactive_hours: int = 24) -> int:
        """
        Clean up inactive sessions

        Args:
            max_inactive_hours: Maximum hours of inactivity before cleanup

        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.now().timestamp()
        max_inactive_seconds = max_inactive_hours * 3600
        cleaned_up = 0

        inactive_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if current_time - session.last_activity > max_inactive_seconds
        ]

        for session_id in inactive_sessions:
            if self.terminate_session(session_id):
                cleaned_up += 1

        if cleaned_up > 0:
            logger.info(f"Cleaned up {cleaned_up} inactive sessions")

        return cleaned_up

    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        total_participants = sum(
            len(session.participants)
            for session in self._sessions.values()
        )

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": sum(
                1 for s in self._sessions.values()
                if s.state == SessionState.ACTIVE
            ),
            "total_participants": total_participants,
            "sessions_dir": str(self.sessions_dir),
        }
