"""FastAPI application factory with lifespan management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logging_config import setup_logging
from app.middleware import LoggingMiddleware
from app.middleware.exception_handler import setup_exception_handlers

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: initialise logging and attempt DB connection. Shutdown: close pool."""
    setup_logging()
    logger.info("Application startup", extra={"environment": settings.ENVIRONMENT})
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.warning(
            "Database initialization failed — endpoints requiring DB will error",
            extra={"error": str(exc)},
        )
    yield
    logger.info("Application shutdown")
    try:
        await close_db()
    except Exception as exc:
        logger.warning("Database close failed", extra={"error": str(exc)})


def create_app() -> FastAPI:
    """Create and return a configured FastAPI application instance."""
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.PROJECT_VERSION,
        docs_url=settings.API_DOCS_URL,
        redoc_url=settings.API_REDOC_URL,
        openapi_url=settings.API_OPENAPI_URL,
        lifespan=lifespan,
    )

    setup_exception_handlers(app)

    # Allow configured origins + any GitHub Codespaces / Render preview origin
    _CODESPACES_REGEX = (
        r"https://[a-z0-9\-]+-\d+\.app\.github\.dev"        # Codespaces forwarded ports
        r"|https://[a-z0-9\-]+\.preview\.app\.github\.dev"  # Codespaces preview URLs
        r"|https://.*\.onrender\.com"                        # Render preview deployments
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=_CODESPACES_REGEX,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )
    app.add_middleware(LoggingMiddleware)


    # Include WebSocket router — mounted under the same /api/v1 prefix
    from app.websockets.router import ws_router
    app.include_router(ws_router, prefix=settings.API_PREFIX)
    app.include_router(v1_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
