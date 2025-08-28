"""
Job queue interface and implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
import structlog

logger = structlog.get_logger()


class JobQueueInterface(ABC):
    """Interface for job queue implementations."""
    
    @abstractmethod
    async def enqueue(self, job_data: dict, priority: int = 0) -> str:
        """Enqueue a job with optional priority."""
        pass
    
    @abstractmethod
    async def dequeue(self, queue_name: str) -> Optional[dict]:
        """Dequeue a job from a specific queue."""
        pass
    
    @abstractmethod
    async def get_job_status(self, job_id: str) -> dict:
        """Get the status of a specific job."""
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job."""
        pass


class InMemoryJobQueue(JobQueueInterface):
    """Simple in-memory job queue for development/testing."""
    
    def __init__(self):
        self.jobs: dict[str, dict] = {}
        self.queue: list[tuple[int, str, dict]] = []
        self.job_counter = 0
    
    async def enqueue(self, job_data: dict, priority: int = 0) -> str:
        """Enqueue a job with priority."""
        job_id = f"job_{self.job_counter}"
        self.job_counter += 1
        
        job_info = {
            "id": job_id,
            "data": job_data,
            "priority": priority,
            "status": "queued",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        self.jobs[job_id] = job_info
        
        # Insert with priority (higher priority first)
        self.queue.append((priority, job_id, job_data))
        self.queue.sort(key=lambda x: x[0], reverse=True)
        
        logger.info(
            "Job enqueued",
            job_id=job_id,
            priority=priority
        )
        
        return job_id
    
    async def dequeue(self, queue_name: str) -> Optional[dict]:
        """Dequeue a job from the queue."""
        if not self.queue:
            return None
        
        priority, job_id, job_data = self.queue.pop(0)
        
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = "processing"
        
        logger.info(
            "Job dequeued",
            job_id=job_id,
            priority=priority
        )
        
        return {
            "id": job_id,
            "data": job_data,
            "priority": priority
        }
    
    async def get_job_status(self, job_id: str) -> dict:
        """Get job status."""
        if job_id not in self.jobs:
            return {"status": "not_found"}
        
        return self.jobs[job_id]
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        if job_id not in self.jobs:
            return False
        
        # Remove from queue if still there
        self.queue = [
            (p, jid, data) for p, jid, data in self.queue 
            if jid != job_id
        ]
        
        # Update status
        self.jobs[job_id]["status"] = "cancelled"
        
        logger.info("Job cancelled", job_id=job_id)
        return True


class RedisJobQueue(JobQueueInterface):
    """Redis-based job queue for production use."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def enqueue(self, job_data: dict, priority: int = 0) -> str:
        """Enqueue a job using Redis."""
        try:
            import uuid
            job_id = str(uuid.uuid4())
            
            job_info = {
                "id": job_id,
                "data": job_data,
                "priority": priority,
                "status": "queued",
                "created_at": "2024-01-01T00:00:00Z"
            }
            
            # Store job data
            await self.redis.hset(f"job:{job_id}", mapping=job_info)
            
            # Add to priority queue
            await self.redis.zadd("job_queue", {job_id: priority})
            
            logger.info(
                "Job enqueued in Redis",
                job_id=job_id,
                priority=priority
            )
            
            return job_id
            
        except Exception as e:
            logger.error(
                "Failed to enqueue job in Redis",
                error=str(e)
            )
            raise
    
    async def dequeue(self, queue_name: str) -> Optional[dict]:
        """Dequeue a job from Redis queue."""
        try:
            # Get highest priority job
            job_ids = await self.redis.zrevrange("job_queue", 0, 0)
            
            if not job_ids:
                return None
            
            job_id = job_ids[0].decode()
            
            # Remove from queue
            await self.redis.zrem("job_queue", job_id)
            
            # Get job data
            job_data = await self.redis.hgetall(f"job:{job_id}")
            
            if job_data:
                # Update status
                await self.redis.hset(f"job:{job_id}", "status", "processing")
                
                logger.info(
                    "Job dequeued from Redis",
                    job_id=job_id
                )
                
                return {
                    "id": job_id,
                    "data": job_data.get(b"data", {}),
                    "priority": int(job_data.get(b"priority", 0))
                }
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to dequeue job from Redis",
                error=str(e)
            )
            return None
    
    async def get_job_status(self, job_id: str) -> dict:
        """Get job status from Redis."""
        try:
            job_data = await self.redis.hgetall(f"job:{job_id}")
            
            if not job_data:
                return {"status": "not_found"}
            
            return {
                "id": job_id,
                "status": job_data.get(b"status", b"unknown").decode(),
                "priority": int(job_data.get(b"priority", 0)),
                "created_at": job_data.get(b"created_at", b"").decode()
            }
            
        except Exception as e:
            logger.error(
                "Failed to get job status from Redis",
                job_id=job_id,
                error=str(e)
            )
            return {"status": "error"}
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job in Redis."""
        try:
            # Remove from queue
            await self.redis.zrem("job_queue", job_id)
            
            # Update status
            await self.redis.hset(f"job:{job_id}", "status", "cancelled")
            
            logger.info("Job cancelled in Redis", job_id=job_id)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to cancel job in Redis",
                job_id=job_id,
                error=str(e)
            )
            return False
