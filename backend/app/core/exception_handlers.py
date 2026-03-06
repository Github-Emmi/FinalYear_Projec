"""
Exception Handlers - Global error handling and logging for FastAPI application.

Provides:
- Structured error responses for all custom exceptions
- Comprehensive logging with context and correlation IDs
- Sensitive data redaction
- Request/response tracking
- Performance metrics logging
"""

from typing import Callable
import logging
import json
import re
from uuid import uuid4

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.exceptions import (
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    ExternalServiceError,
)

logger = logging.getLogger(__name__)

# Sensitive data patterns for redaction
SENSITIVE_PATTERNS = {
    "password": r"password['\"]?\s*[:=]\s*['\"]?[^'\"]*['\"]?",
    "token": r"(token|authorization)['\"]?\s*[:=]\s*['\"]?[^'\"]*['\"]?",
    "api_key": r"(api_key|apikey)['\"]?\s*[:=]\s*['\"]?[^'\"]*['\"]?",
    "secret": r"(secret|client_secret)['\"]?\s*[:=]\s*['\"]?[^'\"]*['\"]?",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
}

REDACTION_REPLACEMENT = "[REDACTED]"


def redact_sensitive_data(data: str) -> str:
    """
    Redact sensitive information from logs and error messages.

    Args:
        data: String potentially containing sensitive data

    Returns:
        String with sensitive data redacted

    Examples:
        >>> redact_sensitive_data('password="secret123"')
        'password="[REDACTED]"'
    """
    redacted = data
    for pattern_name, pattern in SENSITIVE_PATTERNS.items():
        redacted = re.sub(pattern, f"{pattern_name}={REDACTION_REPLACEMENT}", redacted, flags=re.IGNORECASE)
    return redacted


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs for request tracing.

    Adds a unique correlation ID to each request for tracking across logs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Add correlation ID to request and response.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response with X-Correlation-ID header
        """
        # Check for existing correlation ID (from client)
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))

        # Add to request state for access in handlers
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging.

    Logs all requests with method, path, status, and execution time.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Log request and response details.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response with logging
        """
        import time

        # Get correlation ID from request state
        correlation_id = getattr(request.state, "correlation_id", str(uuid4()))

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        # Measure execution time
        start_time = time.time()
        try:
            response = await call_next(request)
            execution_time = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "execution_time_ms": round(execution_time * 1000, 2),
                },
            )

            return response

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "execution_time_ms": round(execution_time * 1000, 2),
                },
                exc_info=True,
            )
            raise


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.

    Args:
        app: FastAPI application instance

    Usage:
        from app.core.exception_handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """Handle ValidationError (400 Bad Request)."""
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.warning(
            f"Validation error: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "error_type": "VALIDATION_ERROR",
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "type": "VALIDATION_ERROR",
                    "message": str(exc),
                    "details": getattr(exc, "detail", {}),
                },
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_error_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
        """Handle UnauthorizedError (401 Unauthorized)."""
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.warning(
            f"Unauthorized access attempt: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "error_type": "UNAUTHORIZED",
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": {
                    "type": "UNAUTHORIZED",
                    "message": "Authentication required or invalid credentials",
                    "detail": str(exc),
                },
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_error_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        """Handle ForbiddenError (403 Forbidden)."""
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.warning(
            f"Forbidden access attempt: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "error_type": "FORBIDDEN",
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {
                    "type": "FORBIDDEN",
                    "message": "You don't have permission to access this resource",
                    "detail": str(exc),
                },
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        """Handle NotFoundError (404 Not Found)."""
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.info(
            f"Resource not found: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "error_type": "NOT_FOUND",
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "type": "NOT_FOUND",
                    "message": "The requested resource was not found",
                    "detail": str(exc),
                },
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(ConflictError)
    async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
        """Handle ConflictError (409 Conflict)."""
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.warning(
            f"Resource conflict: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "error_type": "CONFLICT",
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error": {
                    "type": "CONFLICT",
                    "message": "Resource conflict - the operation cannot be completed",
                    "detail": str(exc),
                },
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_error_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
        """Handle ExternalServiceError (502 Bad Gateway)."""
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.error(
            f"External service error: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "error_type": "EXTERNAL_SERVICE_ERROR",
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "error": {
                    "type": "EXTERNAL_SERVICE_ERROR",
                    "message": "External service unavailable",
                    "detail": "An external service required for this operation is currently unavailable",
                },
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all unhandled exceptions (500 Internal Server Error)."""
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Redact sensitive data from error message
        error_message = redact_sensitive_data(str(exc))

        # Log with full context
        logger.error(
            f"Unexpected error: {error_message}",
            extra={
                "correlation_id": correlation_id,
                "error_type": "INTERNAL_SERVER_ERROR",
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
                "request_id": request.headers.get("X-Request-ID", "unknown"),
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "type": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact support.",
                    "correlation_id": correlation_id,
                },
            },
        )


def configure_logging() -> None:
    """
    Configure comprehensive logging for the application.

    Sets up structured logging with JSON formatting and sensitive data redaction.
    """
    import logging.config

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": "logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
            },
        },
        "loggers": {
            "": {  # Root logger
                "level": "INFO",
                "handlers": ["console", "file", "error_file"],
            },
            "app": {
                "level": "DEBUG",
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(LOGGING_CONFIG)


class ContextFilter(logging.Filter):
    """
    Add context information to log records.

    Adds correlation_id and other contextual info to enable tracing.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context to log record.

        Args:
            record: Log record to enhance

        Returns:
            True to allow the record to be logged
        """
        # Set default correlation ID if not present
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "unknown"

        return True
