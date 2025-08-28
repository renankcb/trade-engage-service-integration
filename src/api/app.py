"""
FastAPI application factory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.error_handler import ErrorHandlerMiddleware
from src.api.middleware.logging import LoggingMiddleware
from src.api.routes import admin, health, jobs, webhooks
from src.config.logging import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Integration service between TradeEngage and ServiceTitan",
        openapi_url=f"{settings.API_PREFIX}/openapi.json" if settings.DEBUG else None,
        docs_url=f"{settings.API_PREFIX}/docs" if settings.DEBUG else None,
        redoc_url=f"{settings.API_PREFIX}/redoc" if settings.DEBUG else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    ErrorHandlerMiddleware(app)
    LoggingMiddleware(app)

    # Add routes
    app.include_router(health.router, prefix=settings.API_PREFIX, tags=["health"])
    app.include_router(jobs.router, prefix=settings.API_PREFIX, tags=["jobs"])
    app.include_router(webhooks.router, prefix=settings.API_PREFIX, tags=["webhooks"])

    if settings.ENABLE_DEBUG_ROUTES:
        app.include_router(admin.router, prefix=settings.API_PREFIX, tags=["admin"])

    @app.on_event("startup")
    async def startup_event():
        logger.info("Application startup", environment=settings.ENVIRONMENT)

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutdown")

    return app
