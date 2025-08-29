"""
Redis-based queue implementation.
"""

import json
import time
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger()


class RedisQueue:
    """Redis-based queue implementation."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def enqueue(
        self,
        queue_name: str,
        task_data: Dict[str, Any],
        priority: int = 0,
        delay_seconds: int = 0,
    ) -> str:
        """Enqueue a task with priority and optional delay."""
        try:
            import uuid

            task_id = str(uuid.uuid4())

            task_info = {
                "id": task_id,
                "data": task_data,
                "priority": priority,
                "created_at": "2024-01-01T00:00:00Z",
                "status": "queued",
            }

            # Store task data
            await self.redis.hset(f"task:{task_id}", mapping=task_info)

            # Add to priority queue
            if delay_seconds > 0:
                # Use sorted set for delayed tasks
                await self.redis.zadd(f"delayed:{queue_name}", {task_id: priority})
                await self.redis.expire(f"delayed:{queue_name}", delay_seconds + 3600)
            else:
                # Add to immediate queue
                await self.redis.zadd(f"queue:{queue_name}", {task_id: priority})

            logger.info(
                "Task enqueued in Redis",
                task_id=task_id,
                queue=queue_name,
                priority=priority,
                delay=delay_seconds,
            )

            return task_id

        except Exception as e:
            logger.error(
                "Failed to enqueue task in Redis", queue=queue_name, error=str(e)
            )
            raise

    async def dequeue(
        self, queue_name: str, timeout: int = 10
    ) -> Optional[Dict[str, Any]]:
        """Dequeue a task from the queue."""
        try:
            # Check delayed tasks first
            delayed_key = f"delayed:{queue_name}"
            current_time = int(time.time())

            # Get ready delayed tasks
            ready_tasks = await self.redis.zrangebyscore(
                delayed_key, 0, current_time, start=0, num=1
            )

            if ready_tasks:
                # Move from delayed to immediate queue
                task_id = ready_tasks[0].decode()
                await self.redis.zrem(delayed_key, task_id)
                await self.redis.zadd(f"queue:{queue_name}", {task_id: 0})

            # Get highest priority task
            queue_key = f"queue:{queue_name}"
            task_ids = await self.redis.zrevrange(queue_key, 0, 0)

            if not task_ids:
                return None

            task_id = task_ids[0].decode()

            # Remove from queue
            await self.redis.zrem(queue_key, task_id)

            # Get task data
            task_data = await self.redis.hgetall(f"task:{task_id}")

            if task_data:
                # Update status
                await self.redis.hset(f"task:{task_id}", "status", "processing")

                logger.info(
                    "Task dequeued from Redis", task_id=task_id, queue=queue_name
                )

                return {
                    "id": task_id,
                    "data": json.loads(task_data.get(b"data", "{}")),
                    "priority": int(task_data.get(b"priority", 0)),
                }

            return None

        except Exception as e:
            logger.error(
                "Failed to dequeue task from Redis", queue=queue_name, error=str(e)
            )
            return None

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status from Redis."""
        try:
            task_data = await self.redis.hgetall(f"task:{task_id}")

            if not task_data:
                return {"status": "not_found"}

            return {
                "id": task_id,
                "status": task_data.get(b"status", b"unknown").decode(),
                "priority": int(task_data.get(b"priority", 0)),
                "created_at": task_data.get(b"created_at", b"").decode(),
            }

        except Exception as e:
            logger.error(
                "Failed to get task status from Redis", task_id=task_id, error=str(e)
            )
            return {"status": "error"}

    async def cancel_task(self, task_id: str, queue_name: str) -> bool:
        """Cancel a task in Redis."""
        try:
            # Remove from all queues
            await self.redis.zrem(f"queue:{queue_name}", task_id)
            await self.redis.zrem(f"delayed:{queue_name}", task_id)

            # Update status
            await self.redis.hset(f"task:{task_id}", "status", "cancelled")

            logger.info("Task cancelled in Redis", task_id=task_id, queue=queue_name)

            return True

        except Exception as e:
            logger.error(
                "Failed to cancel task in Redis", task_id=task_id, error=str(e)
            )
            return False

    async def get_queue_stats(self, queue_name: str) -> Dict[str, int]:
        """Get queue statistics."""
        try:
            immediate_count = await self.redis.zcard(f"queue:{queue_name}")
            delayed_count = await self.redis.zcard(f"delayed:{queue_name}")

            return {
                "immediate": immediate_count,
                "delayed": delayed_count,
                "total": immediate_count + delayed_count,
            }

        except Exception as e:
            logger.error(
                "Failed to get queue stats from Redis", queue=queue_name, error=str(e)
            )
            return {"immediate": 0, "delayed": 0, "total": 0}

    async def clear_queue(self, queue_name: str) -> int:
        """Clear all tasks from a queue."""
        try:
            immediate_key = f"queue:{queue_name}"
            delayed_key = f"delayed:{queue_name}"

            # Get all task IDs
            immediate_tasks = await self.redis.zrange(immediate_key, 0, -1)
            delayed_tasks = await self.redis.zrange(delayed_key, 0, -1)

            all_tasks = immediate_tasks + delayed_tasks

            # Clear queues
            await self.redis.delete(immediate_key, delayed_key)

            # Clean up task data
            for task_id in all_tasks:
                await self.redis.delete(f"task:{task_id.decode()}")

            cleared_count = len(all_tasks)

            logger.info(
                "Queue cleared in Redis", queue=queue_name, cleared_count=cleared_count
            )

            return cleared_count

        except Exception as e:
            logger.error(
                "Failed to clear queue in Redis", queue=queue_name, error=str(e)
            )
            return 0
