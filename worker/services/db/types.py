import enum
from typing import Dict, Optional, TypeVar, Generic, Any

T = TypeVar('T')

class DBErrorType(enum.Enum):
    """
    Enumeration of possible DB service error types.
    
    These are used to classify API errors for better error handling.
    """
    NOT_FOUND = "NOT_FOUND"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    ECONNABORTED_ERROR = "ECONNABORTED_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    CONFLICT = "CONFLICT"
    FORBIDDEN = "FORBIDDEN"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    STATUS_CODE_ERROR = "STATUS_CODE_ERROR"

# Error status code messages
ERROR_MESSAGES: Dict[int, str] = {
    404: "Resource not found",
    401: "Authentication failed",
    500: "Internal server error",
    429: "Rate limit exceeded",
    400: "Bad request",
    409: "Conflict",
    403: "Forbidden",
    504: "Gateway timeout",
    405: "Method not allowed",
}

class DBServiceError(Exception):
    """Custom exception for DB service errors."""
    
    def __init__(self, error_type: DBErrorType, message: str):
        self.error_type = error_type
        super().__init__(f"{error_type.value}: {message}")

# Types for API responses
class ApiResponse(Generic[T]):
    """Generic API response wrapper."""
    
    def __init__(self, data: Optional[T] = None, success: bool = True, message: str = ""):
        self.data = data
        self.success = success
        self.message = message
        
    @classmethod
    def from_dict(cls, response_dict: Dict[str, Any]) -> 'ApiResponse[T]':
        """Create an ApiResponse from a dictionary."""
        return cls(
            data=response_dict.get('data'),
            success=response_dict.get('success', True),
            message=response_dict.get('message', '')
        ) 