"""
Error handling middleware.
"""

import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from src.config.logging import get_logger
from src.domain.exceptions.provider_error import ProviderError
from src.domain.exceptions.sync_error import SyncError
from src.domain.exceptions.validation_error import ValidationError

logger = get_logger(__name__)


class ErrorHandlerMiddleware:
    """Error handling middleware for FastAPI."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.add_error_handlers()
    
    def add_error_handlers(self) -> None:
        """Add custom error handlers to FastAPI app."""


def add_error_handlers(app: FastAPI) -> None:
    """Add custom error handlers to FastAPI app."""

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        logger.warning("Validation error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation Error",
                "message": str(exc),
                "type": "validation_error",
            },
        )

    @app.exception_handler(SyncError)
    async def sync_error_handler(request: Request, exc: SyncError):
        logger.error("Sync error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=422,
            content={"error": "Sync Error", "message": str(exc), "type": "sync_error"},
        )

    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError):
        logger.error("Provider error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=502,
            content={
                "error": "Provider Error",
                "message": str(exc),
                "type": "provider_error",
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error("Database error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database Error",
                "message": "A database error occurred",
                "type": "database_error",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "message": exc.detail,
                "type": "http_error",
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "type": "internal_error",
            },
        )
