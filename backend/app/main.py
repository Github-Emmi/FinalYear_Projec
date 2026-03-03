"""
FastAPI application factory and initialization
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from uuid import uuid4

from .core.config import get_settings
from .core.database import init_db, close_db
from .core.logging_config import setup_logging
from .middleware.exception_handler import setup_exception_handlers
from .middleware.logging_middleware import LoggingMiddleware

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Application startup")
    setup_logging()
    await init_db()
    logger.info("✅ Database initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Application shutdown")
    await close_db()
    logger.info("✅ Database connections closed")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application instance.
    
    Returns:
        FastAPI application with all middleware and routes configured
    """
    
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.PROJECT_VERSION,
        docs_url=settings.API_DOCS_URL,
        redoc_url=settings.API_REDOC_URL,
        openapi_url=settings.API_OPENAPI_URL,
        lifespan=lifespan,
    )

    # Setup exception handlers
    setup_exception_handlers(app)

    # ==================== MIDDLEWARE ====================
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )

    # Logging middleware (must be last/outermost)
    app.add_middleware(LoggingMiddleware)

    # ==================== ROUTES ====================
    
    # Health check endpoint
    @app.get("/health", tags=["Health Check"])
    async def health_check():
        """Application health check endpoint"""
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": settings.PROJECT_VERSION,
        }

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Welcome endpoint"""
        return {
            "message": "School Management System - Phase 1",
            "version": settings.PROJECT_VERSION,
            "docs": "/docs",
            "api_prefix": settings.API_PREFIX,
        }

    # ==================== API V1 ROUTES ====================
    # Routes will be imported and included here in Phase 2
    # from .api.v1 import router as v1_router
    # app.include_router(v1_router, prefix=settings.API_PREFIX)

    logger.info(f"✅ FastAPI application created with {len(app.routes)} routes")
    return app


# Application instance
app = create_app()
