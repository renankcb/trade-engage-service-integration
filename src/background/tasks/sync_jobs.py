"""
Celery tasks for job synchronization.
"""

import asyncio
from celery import current_app
from uuid import UUID
import structlog

logger = structlog.get_logger()


@current_app.task(
    bind=True,
    max_retries=3,
    name="sync_job_task"
)
def sync_job_task(self, routing_id: str):
    """Sync a specific job routing to its target company."""
    try:
        logger.info(
            "Starting job sync task",
            routing_id=routing_id,
            attempt=self.request.retries + 1,
            max_retries=self.max_retries
        )
        
        # Import here to avoid circular imports
        from src.application.use_cases.sync_job import SyncJobUseCase
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository
        )
        from src.infrastructure.database.repositories.company_repository import (
            CompanyRepository
        )
        from src.infrastructure.database.repositories.job_repository import (
            JobRepository
        )
        from src.infrastructure.providers.factory import ProviderFactory
        from src.application.services.provider_manager import ProviderManager
        from src.application.services.data_transformer import DataTransformer
        
        # Create repositories and services
        job_routing_repo = JobRoutingRepository()
        job_repo = JobRepository()
        company_repo = CompanyRepository()
        provider_factory = ProviderFactory()
        provider_manager = ProviderManager(provider_factory, company_repo)
        data_transformer = DataTransformer()
        
        # Create and execute use case
        use_case = SyncJobUseCase(
            job_routing_repo=job_routing_repo,
            job_repo=job_repo,
            company_repo=company_repo,
            provider_manager=provider_manager,
            data_transformer=data_transformer,
        )
        
        # Convert string to UUID and execute
        routing_uuid = UUID(routing_id)
        result = asyncio.run(use_case.execute(routing_uuid))
        
        if result:
            logger.info(
                "Job sync task completed successfully",
                routing_id=routing_id,
                attempt=self.request.retries + 1
            )
            
            return {
                "status": "success",
                "routing_id": routing_id,
                "external_id": getattr(result, 'external_id', None)
            }
        else:
            logger.warning(
                "Job sync task failed",
                routing_id=routing_id,
                attempt=self.request.retries + 1
            )
            
            return {
                "status": "failed",
                "routing_id": routing_id,
                "reason": "Sync returned False"
            }
        
    except Exception as e:
        logger.error(
            "Job sync task failed with exception",
            routing_id=routing_id,
            error=str(e),
            error_type=type(e).__name__,
            attempt=self.request.retries + 1,
            max_retries=self.max_retries
        )
        
        # Implement manual retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_countdown = 60 * (2 ** self.request.retries)  # 1min, 2min, 4min
            logger.info(
                "Retrying job sync task",
                routing_id=routing_id,
                attempt=self.request.retries + 1,
                next_retry_in_seconds=retry_countdown
            )
            raise self.retry(countdown=retry_countdown)
        
        # Max retries exceeded - log final failure
        logger.error(
            "Job sync task failed permanently after max retries",
            routing_id=routing_id,
            total_attempts=self.request.retries + 1,
            final_error=str(e)
        )
        
        return {
            "status": "permanently_failed",
            "routing_id": routing_id,
            "error": str(e),
            "total_attempts": self.request.retries + 1
        }


@current_app.task(
    bind=True,
    max_retries=2,
    name="sync_pending_jobs_task"
)
def sync_pending_jobs_task(self):
    """Find and sync all pending job routings."""
    try:
        logger.info(
            "Starting pending jobs sync task",
            attempt=self.request.retries + 1,
            max_retries=self.max_retries
        )
        
        # Import here to avoid circular imports
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository
        )
        from src.infrastructure.database.repositories.company_repository import (
            CompanyRepository
        )
        from src.infrastructure.providers.factory import ProviderFactory
        from src.application.services.provider_manager import ProviderManager
        
        # Create repositories and services
        job_routing_repo = JobRoutingRepository()
        company_repo = CompanyRepository()
        provider_factory = ProviderFactory()
        provider_manager = ProviderManager(provider_factory, company_repo)
        
        # IMPLEMENTAR CLAIM PATTERN para evitar duplicatas
        # Buscar e marcar routings como 'processing' atomicamente
        claimed_routings = asyncio.run(job_routing_repo.claim_pending_routings(limit=50))
        
        if not claimed_routings:
            logger.info("No pending routings available for claiming")
            return {
                "status": "success",
                "message": "No pending routings available",
                "processed": 0
            }
        
        # Queue individual sync tasks for each claimed routing
        queued_count = 0
        for routing in claimed_routings:
            try:
                sync_job_task.delay(str(routing.id))
                queued_count += 1
                
                logger.info(
                    "Queued sync task for claimed routing",
                    routing_id=str(routing.id),
                    company_id=str(routing.company_id_received),
                    claim_timestamp=routing.claimed_at
                )
                
            except Exception as e:
                logger.error(
                    "Failed to queue sync task for claimed routing",
                    routing_id=str(routing.id),
                    error=str(e)
                )
                # Mark routing as failed since we couldn't queue it
                asyncio.run(job_routing_repo.mark_sync_failed(
                    routing.id, 
                    f"Failed to queue sync task: {str(e)}"
                ))
        
        logger.info(
            "Pending jobs sync task completed",
            total_claimed=len(claimed_routings),
            queued_tasks=queued_count,
            attempt=self.request.retries + 1
        )
        
        return {
            "status": "success",
            "total_claimed": len(claimed_routings),
            "queued_tasks": queued_count
        }
        
    except Exception as e:
        logger.error(
            "Pending jobs sync task failed with exception",
            error=str(e),
            error_type=type(e).__name__,
            attempt=self.request.retries + 1,
            max_retries=self.max_retries
        )
        
        # Implement manual retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_countdown = 120 * (2 ** self.request.retries)  # 2min, 4min
            logger.info(
                "Retrying pending jobs sync task",
                attempt=self.request.retries + 1,
                next_retry_in_seconds=retry_countdown
            )
            raise self.retry(countdown=retry_countdown)
        
        # Max retries exceeded - log final failure
        logger.error(
            "Pending jobs sync task failed permanently after max retries",
            total_attempts=self.request.retries + 1,
            final_error=str(e)
        )
        
        return {
            "status": "permanently_failed",
            "error": str(e),
            "total_attempts": self.request.retries + 1
        }


@current_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    name="poll_synced_jobs_task"
)
def poll_synced_jobs_task(self):
    """Poll for updates on synced jobs."""
    try:
        logger.info(
            "Starting synced jobs polling task",
            attempt=self.request.retries + 1
        )
        
        # Import here to avoid circular imports
        from src.application.use_cases.poll_updates import PollUpdatesUseCase
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository
        )
        from src.infrastructure.database.repositories.job_repository import (
            JobRepository
        )
        from src.infrastructure.database.repositories.company_repository import (
            CompanyRepository
        )
        from src.infrastructure.providers.factory import ProviderFactory
        from src.application.services.provider_manager import ProviderManager
        
        # Create repositories and services
        job_routing_repo = JobRoutingRepository()
        job_repo = JobRepository()
        company_repo = CompanyRepository()
        provider_factory = ProviderFactory()
        provider_manager = ProviderManager(provider_factory, company_repo)
        
        # Create and execute use case
        use_case = PollUpdatesUseCase(
            job_routing_repo=job_routing_repo,
            company_repo=company_repo,
            job_repo=job_repo,
            provider_manager=provider_manager,
        )
        
        result = asyncio.run(use_case.execute())
        
        logger.info(
            "Synced jobs polling task completed",
            jobs_checked=result.total_polled,
            jobs_updated=result.updated,
            jobs_completed=result.completed
        )
        
        return {
            "status": "success",
            "jobs_checked": result.total_polled,
            "jobs_updated": result.updated,
            "jobs_completed": result.completed
        }
        
    except Exception as e:
        logger.error(
            "Synced jobs polling task failed",
            error=str(e),
            attempt=self.request.retries + 1
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise


@current_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    name="retry_failed_jobs_task"
)
def retry_failed_jobs_task(self):
    """Find and retry failed job routings."""
    try:
        logger.info(
            "Starting failed jobs retry task",
            attempt=self.request.retries + 1
        )
        
        # Import here to avoid circular imports
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository
        )
        
        # Create repository
        job_routing_repo = JobRoutingRepository()
        
        # Find failed routings that should be retried
        failed_routings = asyncio.run(job_routing_repo.find_failed_for_retry(limit=25))
        
        if not failed_routings:
            logger.info("No failed routings to retry")
            return {
                "status": "success",
                "message": "No failed routings to retry",
                "retried": 0
            }
        
        # Reset and queue retry for each failed routing
        retried_count = 0
        for routing in failed_routings:
            try:
                if routing.should_retry():
                    routing.reset_for_retry()
                    asyncio.run(job_routing_repo.update(routing))
                    
                    # Queue sync task
                    sync_job_task.delay(str(routing.id))
                    retried_count += 1
                    
                    logger.info(
                        "Failed routing queued for retry",
                        routing_id=str(routing.id),
                        retry_count=routing.retry_count
                    )
                    
            except Exception as e:
                logger.error(
                    "Failed to retry routing",
                    routing_id=str(routing.id),
                    error=str(e)
                )
        
        logger.info(
            "Failed jobs retry task completed",
            total_failed=len(failed_routings),
            retried=retried_count
        )
        
        return {
            "status": "success",
            "total_failed": len(failed_routings),
            "retried": retried_count
        }
        
    except Exception as e:
        logger.error(
            "Failed jobs retry task failed",
            error=str(e),
            attempt=self.request.retries + 1
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise


@current_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    name="retry_failed_job_task"
)
def retry_failed_job_task(self, routing_id: str):
    """Retry a specific failed job routing."""
    try:
        logger.info(
            "Starting individual job retry task",
            routing_id=routing_id,
            attempt=self.request.retries + 1
        )
        
        # Import here to avoid circular imports
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository
        )
        
        # Create repository
        job_routing_repo = JobRoutingRepository()
        
        # Get the routing
        routing_uuid = UUID(routing_id)
        routing = asyncio.run(job_routing_repo.get_by_id(routing_uuid))
        
        if not routing:
            logger.error("Job routing not found", routing_id=routing_id)
            return {
                "status": "error",
                "message": "Job routing not found"
            }
        
        # Check if it can be retried
        if not routing.should_retry():
            logger.warning(
                "Job routing cannot be retried",
                routing_id=routing_id,
                sync_status=routing.sync_status.value,
                retry_count=routing.retry_count
            )
            return {
                "status": "skipped",
                "message": "Cannot be retried"
            }
        
        # Reset for retry
        routing.reset_for_retry()
        asyncio.run(job_routing_repo.update(routing))
        
        # Queue sync task
        sync_job_task.delay(str(routing.id))
        
        logger.info(
            "Individual job retry task completed",
            routing_id=routing_id,
            retry_count=routing.retry_count
        )
        
        return {
            "status": "success",
            "routing_id": routing_id,
            "retry_count": routing.retry_count
        }
        
    except Exception as e:
        logger.error(
            "Individual job retry task failed",
            routing_id=routing_id,
            error=str(e),
            attempt=self.request.retries + 1
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise
