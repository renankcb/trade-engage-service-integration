"""
Cleanup tasks for job maintenance and system cleanup.
"""

import asyncio
from datetime import datetime, timedelta
from uuid import UUID
from celery import current_app
import structlog

from src.infrastructure.database.repositories.job_repository import JobRepository
from src.infrastructure.database.repositories.job_routing_repository import JobRoutingRepository
from src.application.services.transactional_outbox import TransactionalOutbox
from src.config.logging import get_logger

logger = get_logger(__name__)


@current_app.task(
    bind=True,
    max_retries=2,
    name="cleanup_completed_jobs_task"
)
def cleanup_completed_jobs_task(self):
    """Clean up completed jobs and their routings."""
    try:
        logger.info(
            "Starting completed jobs cleanup task",
            attempt=self.request.retries + 1,
            max_retries=self.max_retries
        )
        
        # Import here to avoid circular imports
        from src.infrastructure.database.repositories.job_repository import (
            JobRepository
        )
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository
        )
        
        # Create repositories
        job_repo = JobRepository()
        job_routing_repo = JobRoutingRepository()
        
        # Clean up jobs completed more than 30 days ago
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Find old completed jobs
        old_completed_jobs = asyncio.run(
            job_repo.find_completed_before(cutoff_date, limit=100)
        )
        
        if not old_completed_jobs:
            logger.info("No old completed jobs found for cleanup")
            return {
                "status": "success",
                "message": "No cleanup needed",
                "jobs_cleaned": 0,
                "routings_cleaned": 0
            }
        
        # Clean up each job and its routings
        jobs_cleaned = 0
        routings_cleaned = 0
        
        for job in old_completed_jobs:
            try:
                # Delete job routings first (foreign key constraint)
                job_routings = asyncio.run(
                    job_routing_repo.find_by_job_id(job.id)
                )
                
                for routing in job_routings:
                    asyncio.run(job_routing_repo.delete(routing.id))
                    routings_cleaned += 1
                
                # Delete the job
                asyncio.run(job_repo.delete(job.id))
                jobs_cleaned += 1
                
                logger.info(
                    "Cleaned up completed job",
                    job_id=str(job.id),
                    completed_at=job.completed_at.isoformat() if job.completed_at else None
                )
                
            except Exception as e:
                logger.error(
                    "Error cleaning up job",
                    job_id=str(job.id),
                    error=str(e)
                )
        
        logger.info(
            "Completed jobs cleanup finished",
            jobs_cleaned=jobs_cleaned,
            routings_cleaned=routings_cleaned,
            attempt=self.request.retries + 1
        )
        
        return {
            "status": "success",
            "jobs_cleaned": jobs_cleaned,
            "routings_cleaned": routings_cleaned,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Completed jobs cleanup task failed",
            error=str(e),
            attempt=self.request.retries + 1
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300)  # 5 minutes
        
        return {
            "status": "failed",
            "error": str(e),
            "total_attempts": self.request.retries + 1
        }


@current_app.task(
    bind=True,
    max_retries=2,
    name="cleanup_failed_jobs_task"
)
def cleanup_failed_jobs_task(self):
    """Clean up failed jobs and routings that are too old to retry."""
    try:
        logger.info(
            "Starting failed jobs cleanup task",
            attempt=self.request.retries + 1,
            max_retries=self.max_retries
        )
        
        # Import here to avoid circular imports
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository
        )
        
        # Create repository
        job_routing_repo = JobRoutingRepository()
        
        # Clean up failed routings older than 7 days that can't be retried
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        # Find old failed routings
        old_failed_routings = asyncio.run(
            job_routing_repo.find_failed_before(cutoff_date, limit=100)
        )
        
        if not old_failed_routings:
            logger.info("No old failed routings found for cleanup")
            return {
                "status": "success",
                "message": "No cleanup needed",
                "routings_cleaned": 0
            }
        
        # Clean up each failed routing
        routings_cleaned = 0
        
        for routing in old_failed_routings:
            try:
                # Check if routing can still be retried
                if routing.should_retry():
                    logger.info(
                        "Skipping routing that can still be retried",
                        routing_id=str(routing.id),
                        retry_count=routing.retry_count,
                        max_retries=routing.max_retries
                    )
                    continue
                
                # Delete the failed routing
                asyncio.run(job_routing_repo.delete(routing.id))
                routings_cleaned += 1
                
                logger.info(
                    "Cleaned up failed routing",
                    routing_id=str(routing.id),
                    failed_at=routing.updated_at.isoformat(),
                    retry_count=routing.retry_count,
                    error_message=routing.error_message
                )
                
            except Exception as e:
                logger.error(
                    "Error cleaning up failed routing",
                    routing_id=str(routing.id),
                    error=str(e)
                )
        
        logger.info(
            "Failed jobs cleanup finished",
            routings_cleaned=routings_cleaned,
            attempt=self.request.retries + 1
        )
        
        return {
            "status": "success",
            "routings_cleaned": routings_cleaned,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Failed jobs cleanup task failed",
            error=str(e),
            attempt=self.request.retries + 1
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=600)  # 10 minutes
        
        return {
            "status": "failed",
            "error": str(e),
            "total_attempts": self.request.retries + 1
        }


@current_app.task(
    bind=True,
    max_retries=1,
    name="cleanup_outbox_events_task"
)
def cleanup_outbox_events_task(self):
    """Clean up old completed outbox events."""
    try:
        logger.info(
            "Starting outbox events cleanup task",
            attempt=self.request.retries + 1
        )
        
        # Import here to avoid circular imports
        from src.application.services.transactional_outbox import TransactionalOutbox
        
        # Create outbox service
        outbox = TransactionalOutbox(None)  # Will use default session
        
        # Clean up events completed more than 24 hours ago
        cutoff_date = datetime.utcnow() - timedelta(hours=24)
        
        # Clean up old events
        cleaned_count = asyncio.run(
            outbox.cleanup_completed_events(cutoff_date)
        )
        
        logger.info(
            "Outbox events cleanup finished",
            events_cleaned=cleaned_count,
            cutoff_date=cutoff_date.isoformat()
        )
        
        return {
            "status": "success",
            "events_cleaned": cleaned_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Outbox events cleanup task failed",
            error=str(e),
            attempt=self.request.retries + 1
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=1800)  # 30 minutes
        
        return {
            "status": "failed",
            "error": str(e),
            "total_attempts": self.request.retries + 1
        }


@current_app.task(
    bind=True,
    max_retries=1,
    name="cleanup_orphaned_routings_task"
)
def cleanup_orphaned_routings_task(self):
    """Clean up job routings that reference non-existent jobs."""
    try:
        logger.info(
            "Starting orphaned routings cleanup task",
            attempt=self.request.retries + 1
        )
        
        # Import here to avoid circular imports
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository
        )
        from src.infrastructure.database.repositories.job_repository import (
            JobRepository
        )
        
        # Create repositories
        job_routing_repo = JobRoutingRepository()
        job_repo = JobRepository()
        
        # Find orphaned routings (routings without jobs)
        orphaned_routings = asyncio.run(
            job_routing_repo.find_orphaned_routings(limit=100)
        )
        
        if not orphaned_routings:
            logger.info("No orphaned routings found for cleanup")
            return {
                "status": "success",
                "message": "No cleanup needed",
                "routings_cleaned": 0
            }
        
        # Clean up each orphaned routing
        routings_cleaned = 0
        
        for routing in orphaned_routings:
            try:
                # Delete the orphaned routing
                asyncio.run(job_routing_repo.delete(routing.id))
                routings_cleaned += 1
                
                logger.info(
                    "Cleaned up orphaned routing",
                    routing_id=str(routing.id),
                    job_id=str(routing.job_id),
                    company_id=str(routing.company_id_received)
                )
                
            except Exception as e:
                logger.error(
                    "Error cleaning up orphaned routing",
                    routing_id=str(routing.id),
                    error=str(e)
                )
        
        logger.info(
            "Orphaned routings cleanup finished",
            routings_cleaned=routings_cleaned
        )
        
        return {
            "status": "success",
            "routings_cleaned": routings_cleaned
        }
        
    except Exception as e:
        logger.error(
            "Orphaned routings cleanup task failed",
            error=str(e),
            attempt=self.request.retries + 1
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=3600)  # 1 hour
        
        return {
            "status": "failed",
            "error": str(e),
            "total_attempts": self.request.retries + 1
        }
