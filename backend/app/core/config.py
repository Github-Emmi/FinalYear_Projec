"""Application settings loaded from environment variables via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Project ────────────────────────────────────────────────────────────────
    PROJECT_NAME: str = "School Management System"
    PROJECT_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _parse_debug(cls, value):
        """Allow common non-boolean env values (e.g. DEBUG=release) without crashing.

        Some environments export build-mode strings into DEBUG. Treat production-like
        values as False and development-like values as True.
        """
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            truthy = {"1", "true", "t", "yes", "y", "on", "debug", "dev", "development"}
            falsy = {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}
            if normalized in truthy:
                return True
            if normalized in falsy:
                return False
        return value

    # ── Server ─────────────────────────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    RELOAD: bool = Field(default=True)
    WORKERS: int = Field(default=1)

    # ── Database ───────────────────────────────────────────────────────────────
    DB_DRIVER: str = Field(default="postgresql")
    DB_USER: str = Field(default="school_user")
    DB_PASSWORD: str = Field(default="school_password")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="school_management")
    DB_POOL_SIZE: int = Field(default=20)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_ECHO: bool = Field(default=False)

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"{self.DB_DRIVER}+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: Optional[str] = Field(default=None)

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── RabbitMQ ───────────────────────────────────────────────────────────────
    RABBITMQ_USER: str = Field(default="guest")
    RABBITMQ_PASSWORD: str = Field(default="guest")
    RABBITMQ_HOST: str = Field(default="localhost")
    RABBITMQ_PORT: int = Field(default=5672)
    RABBITMQ_VHOST: str = Field(default="/")

    @property
    def RABBITMQ_URL(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
        )

    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(default="change-this-in-production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # ── CORS ───────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    CORS_CREDENTIALS: bool = Field(default=True)
    CORS_METHODS: List[str] = Field(default=["*"])
    CORS_HEADERS: List[str] = Field(default=["*"])

    # ── OpenAI ─────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")

    # ── SMTP ───────────────────────────────────────────────────────────────────
    SMTP_HOST: str = Field(default="localhost")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_FROM: str = Field(default="noreply@school.edu")
    SMTP_TLS: bool = Field(default=True)

    # ── API Docs ───────────────────────────────────────────────────────────────
    API_TITLE: str = "School Management System API"
    API_DESCRIPTION: str = "FastAPI backend for School Management System"
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"
    API_OPENAPI_URL: str = "/openapi.json"

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    LOG_FILE: str = Field(default="/tmp/app.log")

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — call this everywhere instead of Settings()."""
    return Settings()
