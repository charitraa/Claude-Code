"""
API errors for Claude Code CLI
"""

from typing import Optional
from enum import Enum


class APIErrorType(Enum):
    """Types of API errors"""
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    VALIDATION = "validation"
    SERVER = "server"
    UNKNOWN = "unknown"


class ClaudeAPIError(Exception):
    """Base exception for Claude API errors"""
    
    def __init__(
        self,
        message: str,
        error_type: APIErrorType = APIErrorType.UNKNOWN,
        status_code: Optional[int] = None,
        is_retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.is_retryable = is_retryable


class RateLimitError(ClaudeAPIError):
    """Rate limit error"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message,
            error_type=APIErrorType.RATE_LIMIT,
            is_retryable=True,
        )
        self.retry_after = retry_after


class AuthenticationError(ClaudeAPIError):
    """Authentication error"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message,
            error_type=APIErrorType.AUTHENTICATION,
            status_code=401,
        )


class PermissionError(ClaudeAPIError):
    """Permission error"""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message,
            error_type=APIErrorType.PERMISSION,
            status_code=403,
        )


class ValidationError(ClaudeAPIError):
    """Validation error"""
    
    def __init__(self, message: str = "Validation failed"):
        super().__init__(
            message,
            error_type=APIErrorType.VALIDATION,
            status_code=400,
        )


class ConnectionError(ClaudeAPIError):
    """Connection error"""
    
    def __init__(self, message: str = "Connection failed"):
        super().__init__(
            message,
            error_type=APIErrorType.CONNECTION,
            is_retryable=True,
        )


class TimeoutError(ClaudeAPIError):
    """Timeout error"""
    
    def __init__(self, message: str = "Request timed out"):
        super().__init__(
            message,
            error_type=APIErrorType.TIMEOUT,
            is_retryable=True,
        )
