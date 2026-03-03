"""
Middleware for request logging, error handling, and request ID tracking
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from time import perf_counter
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests and responses.
    Adds request_id to each request for tracking.
    Measures response time.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and log details
        """
        # Generate unique request ID
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Start timer
        start_time = perf_counter()

        # Skip logging for health checks and docs
        skip_logging = request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]

        if not skip_logging:
            logger.info(
                f"→ {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request error: {str(e)}", extra={"request_id": request_id})
            raise

        # Calculate response time
        process_time = perf_counter() - start_time

        # Add custom header with request ID
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        if not skip_logging:
            logger.info(
                f"← {response.status_code} {request.url.path} ({process_time:.3f}s)",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": process_time,
                },
            )

        return response
