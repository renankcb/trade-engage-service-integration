"""
Request/Response logging middleware.
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response

from src.config.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware:
    """Request/Response logging middleware for FastAPI."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.add_logging_middleware()
    
    def add_logging_middleware(self) -> None:
        """Add request/response logging middleware."""

        @self.app.middleware("http")
        async def logging_middleware(request: Request, call_next: Callable) -> Response:
            # Generate request ID
            request_id = str(uuid.uuid4())

            # Start timer
            start_time = time.time()

            # Log request
            logger.info(
                "Request started",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                query_params=str(request.query_params),
                client_host=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            # Add request ID to request state
            request.state.request_id = request_id

            try:
                # Process request
                response = await call_next(request)

                # Calculate processing time
                process_time = time.time() - start_time

                # Log response
                logger.info(
                    "Request completed",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    process_time=f"{process_time:.4f}s",
                )

                # Add headers
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Process-Time"] = f"{process_time:.4f}"

                return response

            except Exception as e:
                # Calculate processing time
                process_time = time.time() - start_time

                # Log error
                logger.error(
                    "Request failed",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    error=str(e),
                    process_time=f"{process_time:.4f}s",
                )

                raise
