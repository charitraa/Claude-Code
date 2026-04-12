"""
Bridge Authentication
Handles JWT tokens, device registration, and session authentication
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import uuid

logger = logging.getLogger(__name__)

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not available, authentication will be simulated")


class AuthToken:
    """Authentication token"""

    def __init__(
        self,
        token: str,
        expires_at: float,
        user_id: str,
        device_id: str
    ):
        self.token = token
        self.expires_at = expires_at
        self.user_id = user_id
        self.device_id = device_id

    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now().timestamp() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "token": self.token,
            "expires_at": self.expires_at,
            "user_id": self.user_id,
            "device_id": self.device_id
        }


class DeviceInfo:
    """Device information"""

    def __init__(
        self,
        device_id: str,
        device_name: str,
        device_type: str,
        last_seen: float,
        is_trusted: bool = False
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.device_type = device_type
        self.last_seen = last_seen
        self.is_trusted = is_trusted
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "last_seen": self.last_seen,
            "is_trusted": self.is_trusted,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceInfo":
        """Create from dictionary"""
        device = cls(
            device_id=data["device_id"],
            device_name=data["device_name"],
            device_type=data["device_type"],
            last_seen=data["last_seen"],
            is_trusted=data.get("is_trusted", False)
        )
        device.metadata = data.get("metadata", {})
        return device


class PermissionCallback:
    """Permission callback for bridge operations"""

    def __init__(
        self,
        callback_id: str,
        operation: str,
        context: Dict[str, Any]
    ):
        self.callback_id = callback_id
        self.operation = operation
        self.context = context
        self.approved: Optional[bool] = None
        self.timestamp = datetime.now().timestamp()

    def approve(self) -> None:
        """Approve the permission request"""
        self.approved = True

    def deny(self, reason: str = "") -> None:
        """Deny the permission request"""
        self.approved = False
        self.context["denial_reason"] = reason

    def is_pending(self) -> bool:
        """Check if permission is still pending"""
        return self.approved is None

    def is_approved(self) -> bool:
        """Check if permission was approved"""
        return self.approved is True

    def is_denied(self) -> bool:
        """Check if permission was denied"""
        return self.approved is False


class BridgeAuth:
    """
    Bridge authentication manager

    Handles JWT tokens, device registration, and permissions
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_expiry_hours: int = 24,
        auth_dir: Optional[Path] = None
    ):
        """
        Initialize bridge authentication

        Args:
            secret_key: Secret key for JWT signing
            token_expiry_hours: Token expiry time in hours
            auth_dir: Directory to store authentication data
        """
        self.secret_key = secret_key or self._generate_secret_key()
        self.token_expiry_hours = token_expiry_hours
        self.auth_dir = auth_dir or (Path.home() / ".claude" / "bridge" / "auth")
        self.auth_dir.mkdir(parents=True, exist_ok=True)

        # State
        self._current_token: Optional[AuthToken] = None
        self._devices: Dict[str, DeviceInfo] = {}
        self._permission_callbacks: Dict[str, PermissionCallback] = {}

        # Load stored data
        self._load_devices()

    def _generate_secret_key(self) -> str:
        """Generate a secret key"""
        import os
        return hashlib.sha256(os.urandom(32)).hexdigest()

    def _load_devices(self) -> None:
        """Load registered devices from storage"""
        devices_file = self.auth_dir / "devices.json"

        if devices_file.exists():
            try:
                with open(devices_file, 'r') as f:
                    data = json.load(f)

                for device_data in data.get("devices", []):
                    device = DeviceInfo.from_dict(device_data)
                    self._devices[device.device_id] = device

                logger.info(f"Loaded {len(self._devices)} registered devices")

            except Exception as e:
                logger.error(f"Error loading devices: {e}")

    def _save_devices(self) -> None:
        """Save registered devices to storage"""
        devices_file = self.auth_dir / "devices.json"

        try:
            data = {
                "devices": [device.to_dict() for device in self._devices.values()]
            }

            with open(devices_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving devices: {e}")

    def generate_token(
        self,
        user_id: str,
        device_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> AuthToken:
        """
        Generate an authentication token

        Args:
            user_id: User identifier
            device_id: Device identifier
            additional_claims: Additional JWT claims

        Returns:
            AuthToken instance
        """
        if JWT_AVAILABLE:
            # Generate JWT token
            payload = {
                "user_id": user_id,
                "device_id": device_id,
                "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
                "iat": datetime.utcnow(),
                "jti": str(uuid.uuid4()),
            }

            if additional_claims:
                payload.update(additional_claims)

            token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        else:
            # Simulate token (for testing without PyJWT)
            token_data = {
                "user_id": user_id,
                "device_id": device_id,
                "expires_at": (datetime.now() + timedelta(hours=self.token_expiry_hours)).timestamp(),
                "jti": str(uuid.uuid4()),
            }
            token = json.dumps(token_data)

        expires_at = (datetime.now() + timedelta(hours=self.token_expiry_hours)).timestamp()

        auth_token = AuthToken(
            token=token,
            expires_at=expires_at,
            user_id=user_id,
            device_id=device_id
        )

        self._current_token = auth_token
        return auth_token

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate an authentication token

        Args:
            token: Token to validate

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            if JWT_AVAILABLE:
                # Decode and validate JWT
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=["HS256"]
                )
                return payload
            else:
                # Simulate validation
                token_data = json.loads(token)
                if datetime.now().timestamp() > token_data.get("expires_at", 0):
                    return None
                return token_data

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

    def refresh_token(self) -> Optional[AuthToken]:
        """
        Refresh the current authentication token

        Returns:
            New AuthToken if successful, None otherwise
        """
        if not self._current_token:
            return None

        # Generate new token with same user and device
        return self.generate_token(
            user_id=self._current_token.user_id,
            device_id=self._current_token.device_id
        )

    def register_device(
        self,
        device_name: str,
        device_type: str = "desktop",
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeviceInfo:
        """
        Register a new device

        Args:
            device_name: Device name
            device_type: Device type (desktop, mobile, tablet, etc.)
            metadata: Additional device metadata

        Returns:
            DeviceInfo instance
        """
        device_id = self._generate_device_id(device_name, device_type)

        device = DeviceInfo(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            last_seen=datetime.now().timestamp(),
            is_trusted=False
        )

        if metadata:
            device.metadata = metadata

        self._devices[device_id] = device
        self._save_devices()

        logger.info(f"Registered device: {device_name} ({device_id})")
        return device

    def unregister_device(self, device_id: str) -> bool:
        """
        Unregister a device

        Args:
            device_id: Device ID to unregister

        Returns:
            True if unregistered, False if not found
        """
        if device_id in self._devices:
            del self._devices[device_id]
            self._save_devices()
            logger.info(f"Unregistered device: {device_id}")
            return True

        return False

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """
        Get device information

        Args:
            device_id: Device ID

        Returns:
            DeviceInfo or None if not found
        """
        return self._devices.get(device_id)

    def list_devices(self, trusted_only: bool = False) -> List[DeviceInfo]:
        """
        List registered devices

        Args:
            trusted_only: Only return trusted devices

        Returns:
            List of DeviceInfo
        """
        devices = list(self._devices.values())

        if trusted_only:
            devices = [d for d in devices if d.is_trusted]

        return devices

    def trust_device(self, device_id: str) -> bool:
        """
        Mark a device as trusted

        Args:
            device_id: Device ID to trust

        Returns:
            True if successful, False if device not found
        """
        device = self._devices.get(device_id)
        if device:
            device.is_trusted = True
            device.last_seen = datetime.now().timestamp()
            self._save_devices()
            logger.info(f"Trusted device: {device_id}")
            return True

        return False

    def untrust_device(self, device_id: str) -> bool:
        """
        Remove trust from a device

        Args:
            device_id: Device ID to untrust

        Returns:
            True if successful, False if device not found
        """
        device = self._devices.get(device_id)
        if device:
            device.is_trusted = False
            device.last_seen = datetime.now().timestamp()
            self._save_devices()
            logger.info(f"Untrusted device: {device_id}")
            return True

        return False

    def request_permission(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> PermissionCallback:
        """
        Request permission for an operation

        Args:
            operation: Operation requiring permission
            context: Context information

        Returns:
            PermissionCallback for tracking the request
        """
        callback_id = str(uuid.uuid4())

        callback = PermissionCallback(
            callback_id=callback_id,
            operation=operation,
            context=context
        )

        self._permission_callbacks[callback_id] = callback

        logger.info(f"Permission requested for {operation}: {callback_id}")
        return callback

    def get_permission_callback(self, callback_id: str) -> Optional[PermissionCallback]:
        """
        Get a permission callback

        Args:
            callback_id: Callback ID

        Returns:
            PermissionCallback or None if not found
        """
        return self._permission_callbacks.get(callback_id)

    def cleanup_expired_callbacks(self) -> None:
        """Clean up expired permission callbacks"""
        current_time = datetime.now().timestamp()
        expired_callbacks = [
            callback_id
            for callback_id, callback in self._permission_callbacks.items()
            if current_time - callback.timestamp > 300  # 5 minutes
        ]

        for callback_id in expired_callbacks:
            del self._permission_callbacks[callback_id]

        if expired_callbacks:
            logger.debug(f"Cleaned up {len(expired_callbacks)} expired callbacks")

    def _generate_device_id(self, device_name: str, device_type: str) -> str:
        """Generate a unique device ID"""
        # Create a hash of device name, type, and current time
        hash_input = f"{device_name}:{device_type}:{datetime.now().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def get_current_token(self) -> Optional[AuthToken]:
        """Get the current authentication token"""
        return self._current_token

    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        if not self._current_token:
            return False

        return not self._current_token.is_expired()

    def logout(self) -> None:
        """Logout and clear authentication"""
        self._current_token = None
        logger.info("Logged out")
