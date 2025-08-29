"""
Service interfaces for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class RateLimiterInterface(ABC):
    """Interface for rate limiting services."""

    @abstractmethod
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed within rate limit."""
        pass

    @abstractmethod
    async def record_request(self, key: str, window: int) -> None:
        """Record a request for rate limiting."""
        pass

    @abstractmethod
    async def get_remaining_requests(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests allowed within current window."""
        pass

    @abstractmethod
    async def reset_limit(self, key: str) -> None:
        """Reset rate limit for a specific key."""
        pass


class RetryHandlerInterface(ABC):
    """Interface for retry handling services."""

    @abstractmethod
    async def should_retry(self, attempt: int, max_attempts: int) -> bool:
        """Check if operation should be retried."""
        pass

    @abstractmethod
    async def get_delay(
        self, attempt: int, base_delay: float, backoff_factor: float
    ) -> float:
        """Calculate delay before next retry attempt."""
        pass

    @abstractmethod
    async def record_attempt(
        self, operation_id: str, attempt: int, success: bool
    ) -> None:
        """Record retry attempt for monitoring."""
        pass

    @abstractmethod
    async def get_retry_stats(self, operation_id: str) -> Dict[str, Any]:
        """Get retry statistics for an operation."""
        pass
