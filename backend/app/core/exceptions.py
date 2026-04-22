"""Custom exception hierarchy for structured HTTP error responses."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import status


class AppException(Exception):
    """Base class for all application-level exceptions."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"


class ValidationError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "VALIDATION_ERROR"


class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_FAILED"


class AuthorizationError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "RESOURCE_CONFLICT"
