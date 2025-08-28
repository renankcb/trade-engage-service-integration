"""
Rate limiting middleware.
"""

import time
from typing import Callable, Dict, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from src.config.logging import get_logger

logger = get_logger(__name__)


class RateLimiterMiddleware:
    """Rate limiting middleware for FastAPI."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.requests: Dict[str, list] = {}
        self.max_requests = 1000  # Default from settings
        self.window_seconds = 3600  # Default from settings
        self.add_rate_limiter()
    
    def add_rate_limiter(self) -> None:
        """Add rate limiting middleware."""
        
        @self.app.middleware("http")
        async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            
            # Check rate limit
            if not self._is_allowed(client_ip):
                logger.warning("Rate limit exceeded", client_ip=client_ip)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate Limit Exceeded",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": self.window_seconds
                    }
                )
            
            # Process request
            response = await call_next(request)
            return response
    
    def _is_allowed(self, client_ip: str) -> bool:
        """Check if client is within rate limit."""
        now = time.time()
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if now - req_time < self.window_seconds
            ]
        
        # Check if limit exceeded
        if client_ip in self.requests and len(self.requests[client_ip]) >= self.max_requests:
            return False
        
        # Add current request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(now)
        
        return True
