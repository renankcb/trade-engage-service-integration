"""
Application settings using Pydantic BaseSettings.
"""

import os
from typing import Any, Dict, List, Optional, Union

from pydantic import HttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "ServiceTitan Integration Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: Union[str, List[str]] = "*"

    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # Redis / Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True
    CELERY_TASK_TIME_LIMIT: int = 600  # 10 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 480  # 8 minutes

    # ServiceTitan API
    SERVICETITAN_BASE_URL: str = "https://api.servicetitan.io"
    SERVICETITAN_CLIENT_ID: Optional[str] = None
    SERVICETITAN_CLIENT_SECRET: Optional[str] = None
    SERVICETITAN_TENANT_ID: Optional[str] = None
    SERVICETITAN_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"
    SERVICETITAN_SCOPE: str = "read write"
    SERVICETITAN_RATE_LIMIT_REQUESTS: int = 100
    SERVICETITAN_RATE_LIMIT_PERIOD: int = 3600
    SERVICETITAN_REQUEST_TIMEOUT: int = 30

    # Security
    SECRET_KEY: str = "your-super-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-here-change-in-production"

    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp/prometheus_multiproc"
    HEALTH_CHECK_TIMEOUT: int = 5

    # Background Jobs
    SYNC_INTERVAL_MINUTES: int = 30
    PUSH_TIMEOUT_MINUTES: int = 5
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BACKOFF_FACTOR: int = 2
    BATCH_SIZE: int = 50
    WORKER_CONCURRENCY: int = 4
    POLLING_BATCH_SIZE: int = 100

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 1000
    RATE_LIMIT_WINDOW: int = 3600
    RATE_LIMIT_BURST: int = 100

    # External Services
    HTTP_TIMEOUT: int = 30
    HTTP_RETRIES: int = 3
    HTTP_BACKOFF_FACTOR: float = 0.5
    HTTP_MAX_RETRIES: int = 3

    # Development
    MOCK_PROVIDERS: bool = False
    ENABLE_DEBUG_ROUTES: bool = False
    AUTO_RELOAD: bool = False
    ENABLE_SWAGGER: bool = True

    # Database Migration
    RUN_MIGRATIONS: bool = True
    MIGRATION_TIMEOUT: int = 300

    # Background Workers and Tasks Configuration
    BACKGROUND_WORKER_OUTBOX_INTERVAL_SECONDS: int = 30
    BACKGROUND_WORKER_POLL_INTERVAL_SECONDS: int = 60

    # Celery Beat Scheduler Configuration
    CELERY_SYNC_PENDING_JOBS_INTERVAL_SECONDS: int = 120  # 2 minutes
    CELERY_POLL_JOB_UPDATES_INTERVAL_SECONDS: int = 20  # 20 seconds
    CELERY_RETRY_FAILED_JOBS_INTERVAL_SECONDS: int = 600  # 10 minutes
    CELERY_CLEANUP_OUTBOX_EVENTS_INTERVAL_HOURS: int = 12  # 12 hours
    CELERY_CLEANUP_ORPHANED_ROUTINGS_HOUR: int = 2  # 2 AM

    # Task Rate Limits
    CELERY_SYNC_JOB_TASK_RATE_LIMIT: str = "100/m"
    CELERY_SYNC_PENDING_JOBS_TASK_RATE_LIMIT: str = "30/m"
    CELERY_POLL_SYNCED_JOBS_TASK_RATE_LIMIT: str = "12/m"
    CELERY_RETRY_FAILED_JOBS_TASK_RATE_LIMIT: str = "6/m"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["*"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        # Build from individual components if DATABASE_URL is not provided
        user = values.get("POSTGRES_USER", "integration_user")
        password = values.get("POSTGRES_PASSWORD", "integration_pass")
        host = values.get("POSTGRES_SERVER", "localhost")
        db = values.get("POSTGRES_DB", "integration_service")
        return f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db}"

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in ["development", "staging", "production", "test"]:
            raise ValueError(
                "Environment must be one of: development, staging, production, test"
            )
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


# Global settings instance
settings = Settings()
