"""
Application settings and configuration management
Uses python-decouple for environment variable management
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Maps to .env file in project root.
    """

    # ==================== PROJECT INFO ====================
    PROJECT_NAME: str = "School Management System"
    PROJECT_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # ==================== SERVER CONFIG ====================
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    RELOAD: bool = Field(default=True, env="RELOAD")
    WORKERS: int = Field(default=1, env="WORKERS")

    # ==================== DATABASE CONFIG ====================
    DB_DRIVER: str = Field(default="postgresql", env="DB_DRIVER")
    DB_USER: str = Field(default="postgres", env="DB_USER")
    DB_PASSWORD: str = Field(default="postgres", env="DB_PASSWORD")
    DB_HOST: str = Field(default="localhost", env="DB_HOST")
    DB_PORT: int = Field(default=5432, env="DB_PORT")
    DB_NAME: str = Field(default="school_management", env="DB_NAME")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")

    @property
    def DATABASE_URL(self) -> str:
        """Construct database connection string"""
        return (
            f"{self.DB_DRIVER}+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ==================== REDIS CONFIG ====================
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    @property
    def REDIS_URL(self) -> str:
        """Construct Redis connection URL"""
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:"
                f"{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ==================== RABBITMQ CONFIG ====================
    RABBITMQ_USER: str = Field(default="guest", env="RABBITMQ_USER")
    RABBITMQ_PASSWORD: str = Field(default="guest", env="RABBITMQ_PASSWORD")
    RABBITMQ_HOST: str = Field(default="localhost", env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(default=5672, env="RABBITMQ_PORT")
    RABBITMQ_VHOST: str = Field(default="/", env="RABBITMQ_VHOST")

    @property
    def RABBITMQ_URL(self) -> str:
        """Construct RabbitMQ connection URL"""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
        )

    # ==================== SECURITY CONFIG ====================
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production", env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Password requirements
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    # ==================== CORS CONFIG ====================
    CORS_ORIGINS: list = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]

    # ==================== CLOUDINARY CONFIG ====================
    CLOUDINARY_CLOUD_NAME: str = Field(default="dmkcqgan1", env="CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str = Field(default="", env="CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str = Field(default="", env="CLOUDINARY_API_SECRET")

    # ==================== OPENAI CONFIG ====================
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    OPENAI_API_TIMEOUT: int = Field(default=30, env="OPENAI_API_TIMEOUT")

    # ==================== EMAIL CONFIG ====================
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: str = Field(default="", env="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")
    FROM_EMAIL: str = Field(default="noreply@schoolms.com", env="FROM_EMAIL")
    FROM_NAME: str = Field(default="School Management System", env="FROM_NAME")

    # ==================== LOGGING CONFIG ====================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: str = "/tmp/app.log"

    # ==================== API CONFIG ====================
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"
    API_OPENAPI_URL: str = "/openapi.json"
    API_TITLE: str = "School Management System API"
    API_DESCRIPTION: str = (
        "Enterprise-grade Learning Management System (LMS) for schools. "
        "Phase 1: FastAPI + PostgreSQL + Redis Backend"
    )

    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get settings instance (cached).
    Called once, returns same instance for all requests.
    """
    return Settings()
