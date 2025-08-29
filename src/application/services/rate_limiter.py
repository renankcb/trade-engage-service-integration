"""
Rate Limiter service for controlling API call frequencies.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.config.logging import get_logger

logger = get_logger(__name__)


class RateLimiterInterface:
    """Interface for rate limiting operations."""

    async def check_rate_limit(
        self, key: str, max_requests: int = 100, window_seconds: int = 60
    ) -> bool:
        """Check if request is allowed within rate limit."""
        raise NotImplementedError

    async def increment_request_count(self, key: str) -> int:
        """Increment request count for a key."""
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiterInterface):
    """In-memory rate limiter for development/testing."""

    def __init__(self):
        self.request_counts = {}
        self.window_starts = {}
        self.logger = logger

    async def check_rate_limit(
        self, key: str, max_requests: int = 100, window_seconds: int = 60
    ) -> bool:
        """Check if request is allowed within rate limit."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)

        # Clean old entries
        if key in self.window_starts and self.window_starts[key] < window_start:
            self.request_counts[key] = 0
            self.window_starts[key] = now

        # Initialize if not exists
        if key not in self.request_counts:
            self.request_counts[key] = 0
            self.window_starts[key] = now

        # Check limit
        if self.request_counts[key] >= max_requests:
            self.logger.warning(
                "Rate limit exceeded",
                key=key,
                current_count=self.request_counts[key],
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            return False

        return True

    async def increment_request_count(self, key: str) -> int:
        """Increment request count for a key."""
        if key not in self.request_counts:
            self.request_counts[key] = 0

        self.request_counts[key] += 1
        return self.request_counts[key]


class RedisRateLimiter(RateLimiterInterface):
    """Redis-based rate limiter for production."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.logger = logger

    async def check_rate_limit(
        self, key: str, max_requests: int = 100, window_seconds: int = 60
    ) -> bool:
        """Check if request is allowed within rate limit using Redis."""
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Get current count
            current_key = (
                f"rate_limit:{key}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
            )
            pipe.get(current_key)
            pipe.ttl(current_key)

            results = pipe.execute()
            current_count = int(results[0]) if results[0] else 0
            ttl = results[1]

            # Check if limit exceeded
            if current_count >= max_requests:
                self.logger.warning(
                    "Rate limit exceeded",
                    key=key,
                    current_count=current_count,
                    max_requests=max_requests,
                    window_seconds=window_seconds,
                )
                return False

            # Set TTL if key doesn't exist
            if ttl == -1:
                pipe.expire(current_key, window_seconds)

            return True

        except Exception as e:
            self.logger.error("Error checking rate limit", key=key, error=str(e))
            # Allow request if rate limiter fails
            return True

    async def increment_request_count(self, key: str) -> int:
        """Increment request count for a key using Redis."""
        try:
            current_key = (
                f"rate_limit:{key}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
            )

            # Increment count atomically
            count = self.redis.incr(current_key)

            # Set TTL if this is the first increment
            if count == 1:
                self.redis.expire(current_key, 3600)  # 1 hour TTL

            return count

        except Exception as e:
            self.logger.error("Error incrementing request count", key=key, error=str(e))
            return 0


class RateLimiter:
    """Main rate limiter service."""

    def __init__(self, redis_client=None):
        if redis_client:
            self.limiter = RedisRateLimiter(redis_client)
        else:
            self.limiter = InMemoryRateLimiter()

        self.logger = logger

    async def check_rate_limit(
        self, key: str, max_requests: int = 100, window_seconds: int = 60
    ) -> bool:
        """Check if request is allowed within rate limit."""
        return await self.limiter.check_rate_limit(key, max_requests, window_seconds)

    async def increment_request_count(self, key: str) -> int:
        """Increment request count for a key."""
        return await self.limiter.increment_request_count(key)

    async def check_and_increment(
        self, key: str, max_requests: int = 100, window_seconds: int = 60
    ) -> bool:
        """Check rate limit and increment count if allowed."""
        if await self.check_rate_limit(key, max_requests, window_seconds):
            await self.increment_request_count(key)
            return True
        return False
