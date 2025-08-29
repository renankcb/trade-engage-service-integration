"""
Redis-based data store for mock provider to persist data between processes.
"""

import asyncio
import json
import os
from typing import Any, Dict, List
from uuid import uuid4

import redis.asyncio as redis

from src.config.logging import get_logger

logger = get_logger(__name__)


class MockDataStore:
    """Redis-based data store for mock provider data."""

    def __init__(self):
        # Don't create Redis client in __init__ to avoid event loop issues
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.namespace = "mock_provider"
        logger.info(f"MockDataStore initialized with Redis URL: {self.redis_url}")

    async def _get_redis_client(self):
        """Get a fresh Redis client for the current event loop."""
        try:
            client = redis.from_url(self.redis_url)
            return client
        except Exception as e:
            logger.error(f"Failed to create Redis client: {e}")
            raise

    async def _get_key(self, key: str) -> str:
        """Get namespaced Redis key."""
        return f"{self.namespace}:{key}"

    async def store_job(self, external_id: str, job_data: Dict[str, Any]) -> None:
        """Store a job in the Redis data store."""
        client = None
        try:
            client = await self._get_redis_client()
            key = await self._get_key(f"job:{external_id}")

            # Convert datetime objects to strings for JSON serialization
            serializable_data = self._make_serializable(job_data)
            await client.set(key, json.dumps(serializable_data))

            # Add to job list for easy enumeration
            await client.sadd(await self._get_key("jobs"), external_id)

            logger.info(
                "Job stored in Redis data store", external_id=external_id, key=key
            )
        except Exception as e:
            logger.error(f"Failed to store job in Redis: {e}")
            raise
        finally:
            if client:
                await client.close()

    async def get_job(self, external_id: str) -> Dict[str, Any]:
        """Get a job from the Redis data store."""
        client = None
        try:
            client = await self._get_redis_client()
            key = await self._get_key(f"job:{external_id}")
            data = await client.get(key)

            if data:
                job_data = json.loads(data)
                logger.info(
                    "Job retrieved from Redis data store", external_id=external_id
                )
                return job_data
            else:
                # Get available jobs for debugging
                available_jobs = await self.list_jobs()
                logger.warning(
                    "Job not found in Redis data store",
                    external_id=external_id,
                    available_jobs=available_jobs,
                    store_size=len(available_jobs),
                )
                return None
        except Exception as e:
            logger.error(f"Failed to get job from Redis: {e}")
            return None
        finally:
            if client:
                await client.close()

    async def update_job(self, external_id: str, updates: Dict[str, Any]) -> bool:
        """Update a job in the Redis data store."""
        client = None
        try:
            client = await self._get_redis_client()
            key = await self._get_key(f"job:{external_id}")
            existing_data = await client.get(key)

            if existing_data:
                job_data = json.loads(existing_data)
                job_data.update(updates)

                # Convert datetime objects to strings
                serializable_data = self._make_serializable(job_data)
                await client.set(key, json.dumps(serializable_data))

                logger.info(
                    "Job updated in Redis data store",
                    external_id=external_id,
                    updates=updates,
                )
                return True
            else:
                logger.warning(
                    "Cannot update job - not found in store", external_id=external_id
                )
                return False
        except Exception as e:
            logger.error(f"Failed to update job in Redis: {e}")
            return False
        finally:
            if client:
                await client.close()

    async def list_jobs(self) -> List[str]:
        """List all job external IDs in the store."""
        client = None
        try:
            client = await self._get_redis_client()
            key = await self._get_key("jobs")
            jobs = await client.smembers(key)
            job_list = [job.decode("utf-8") for job in jobs]
            logger.info(f"Listing jobs from Redis store: {job_list}")
            return job_list
        except Exception as e:
            logger.error(f"Failed to list jobs from Redis: {e}")
            return []
        finally:
            if client:
                await client.close()

    async def clear_store(self) -> None:
        """Clear all stored data (useful for testing)."""
        client = None
        try:
            client = await self._get_redis_client()
            # Get all keys in namespace
            pattern = await self._get_key("*")
            keys = await client.keys(pattern)

            if keys:
                await client.delete(*keys)

            logger.info(f"Redis data store cleared: {len(keys)} keys removed")
        except Exception as e:
            logger.error(f"Failed to clear Redis store: {e}")
        finally:
            if client:
                await client.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the data store."""
        try:
            # This is a sync method, so we can't use async Redis calls
            # Return basic info
            stats = {
                "store_type": "redis",
                "namespace": self.namespace,
                "redis_url": self.redis_url,
            }
            logger.info(f"MockDataStore stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    def _make_serializable(self, data: Any) -> Any:
        """Convert data to be JSON serializable."""
        if isinstance(data, dict):
            return {k: self._make_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._make_serializable(item) for item in data]
        elif hasattr(data, "isoformat"):  # datetime objects
            return data.isoformat()
        elif hasattr(data, "value"):  # enum values
            return data.value
        else:
            return data


# Global instance
mock_data_store = MockDataStore()
logger.info(
    f"Global mock_data_store instance created with Redis namespace: {mock_data_store.namespace}"
)
