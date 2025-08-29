"""
HTTP client utilities for external API calls.
"""

import time
from typing import Any, Dict, Optional

import httpx
import structlog

logger = structlog.get_logger()


class HTTPClient:
    """HTTP client for external API calls."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.client = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make GET request."""
        start_time = time.time()

        try:
            response = await self.client.get(url, headers=headers)

            response_time = (time.time() - start_time) * 1000

            logger.debug(
                "HTTP GET request completed",
                url=url,
                status_code=response.status_code,
                response_time_ms=response_time,
            )

            return response

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            logger.error(
                "HTTP GET request failed",
                url=url,
                error=str(e),
                response_time_ms=response_time,
            )
            raise

    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make POST request."""
        start_time = time.time()

        try:
            response = await self.client.post(url, json=data, headers=headers)

            response_time = (time.time() - start_time) * 1000

            logger.debug(
                "HTTP POST request completed",
                url=url,
                status_code=response.status_code,
                response_time_ms=response_time,
            )

            return response

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            logger.error(
                "HTTP POST request failed",
                url=url,
                error=str(e),
                response_time_ms=response_time,
            )
            raise

    async def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make PUT request."""
        start_time = time.time()

        try:
            response = await self.client.put(url, json=data, headers=headers)

            response_time = (time.time() - start_time) * 1000

            logger.debug(
                "HTTP PUT request completed",
                url=url,
                status_code=response.status_code,
                response_time_ms=response_time,
            )

            return response

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            logger.error(
                "HTTP PUT request failed",
                url=url,
                error=str(e),
                response_time_ms=response_time,
            )
            raise

    async def patch(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make PATCH request."""
        start_time = time.time()

        try:
            response = await self.client.patch(url, json=data, headers=headers)

            response_time = (time.time() - start_time) * 1000

            logger.debug(
                "HTTP PATCH request completed",
                url=url,
                status_code=response.status_code,
                response_time_ms=response_time,
            )

            return response

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            logger.error(
                "HTTP PATCH request failed",
                url=url,
                error=str(e),
                response_time_ms=response_time,
            )
            raise

    async def delete(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make DELETE request."""
        start_time = time.time()

        try:
            response = await self.client.delete(url, headers=headers)

            response_time = (time.time() - start_time) * 1000

            logger.debug(
                "HTTP DELETE request completed",
                url=url,
                status_code=response.status_code,
                response_time_ms=response_time,
            )

            return response

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            logger.error(
                "HTTP DELETE request failed",
                url=url,
                error=str(e),
                response_time_ms=response_time,
            )
            raise


async def get_redis_health() -> Dict[str, Any]:
    """Get Redis health status."""
    try:
        # This would typically check Redis connectivity
        # For now, return a mock response
        return {
            "status": "healthy",
            "response_time_ms": 1.0,
            "memory_usage": 1024 * 1024,  # 1MB
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def make_http_request(
    method: str,
    url: str,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """Make HTTP request with automatic client management."""
    async with HTTPClient(timeout=timeout) as client:
        if method.upper() == "GET":
            return await client.get(url, headers=headers)
        elif method.upper() == "POST":
            return await client.post(url, data=data, headers=headers)
        elif method.upper() == "PUT":
            return await client.put(url, data=data, headers=headers)
        elif method.upper() == "PATCH":
            return await client.patch(url, data=data, headers=headers)
        elif method.upper() == "DELETE":
            return await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
