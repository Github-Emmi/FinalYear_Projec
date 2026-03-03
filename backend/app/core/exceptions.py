"""
Custom exception classes for the application.
Provides structured error handling across the API.
"""

from typing import Optional, Dict, Any


class AppException(Exception):
    """
    Base application exception.
    All custom exceptions inherit from this.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "APP_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Raised when request validation fails"""

    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code=error_code,
            details=details,
        )


class AuthenticationError(AppException):
    """Raised when authentication fails (invalid credentials)"""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTHENTICATION_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code,
            details=details,
        )


class AuthorizationError(AppException):
    """Raised when user lacks required permissions"""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: str = "FORBIDDEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            details=details,
        )


class ResourceNotFoundError(AppException):
    """Raised when a requested resource doesn't exist"""

    def __init__(
        self,
        resource: str,
        resource_id: Any = None,
        error_code: str = "NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        super().__init__(
            message=message,
            status_code=404,
            error_code=error_code,
            details=details,
        )


class ResourceConflictError(AppException):
    """Raised when resource already exists (duplicate)"""

    def __init__(
        self,
        message: str = "Resource already exists",
        error_code: str = "CONFLICT",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code=error_code,
            details=details,
        )


class DatabaseError(AppException):
    """Raised when database operation fails"""

    def __init__(
        self,
        message: str = "Database operation failed",
        error_code: str = "DB_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code=error_code,
            details=details,
        )


class ExternalServiceError(AppException):
    """Raised when external service call fails (OpenAI, Cloudinary, etc.)"""

    def __init__(
        self,
        service: str,
        message: str = "External service error",
        error_code: str = "SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        full_message = f"{service} error: {message}"
        super().__init__(
            message=full_message,
            status_code=503,
            error_code=error_code,
            details=details,
        )


class QuizError(AppException):
    """Raised for quiz-specific errors"""

    def __init__(
        self,
        message: str,
        error_code: str = "QUIZ_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code,
            details=details,
        )


class AttendanceError(AppException):
    """Raised for attendance-specific errors"""

    def __init__(
        self,
        message: str,
        error_code: str = "ATTENDANCE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code,
            details=details,
        )
