"""
Celery tasks for job synchronization.

ARCHITECTURE OVERVIEW:
=====================

1. IMMEDIATE EXECUTION (OutboxWorker):
   - OutboxWorker runs every 30 seconds
   - Processes JOB_SYNC events immediately
   - Calls sync_job_task.delay() for instant processing
   - PRIMARY PATH for job synchronization

2. BACKUP EXECUTION (Celery Beat):
   - sync_pending_jobs_task runs every 2 minutes
   - Only processes jobs that are "stuck" (>5 minutes old)
   - Safety net for jobs missed by OutboxWorker
   - PREVENTS DUPLICATION with immediate execution

3. INDIVIDUAL TASK EXECUTION:
   - sync_job_task processes individual job routings
   - Called by both OutboxWorker (immediate) and backup task
   - Handles the actual sync operation with providers

This architecture ensures:
- ✅ No duplication of work
- ✅ Immediate processing when possible
- ✅ Backup safety net for edge cases
- ✅ Clear separation of concerns
"""

import asyncio
import random
import sys
from uuid import UUID

import structlog
from celery import current_app

logger = structlog.get_logger()


def run_async_in_new_loop(coro):
    """
    Run an async coroutine in a new event loop.

    This function ensures that each Celery task gets its own event loop,
    preventing event loop mixing issues between different processes.
    """
    try:
        # Create a new event loop for this task
        if sys.platform == "win32":
            # Windows-specific event loop policy
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            # Unix-like systems
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the coroutine
        result = loop.run_until_complete(coro)
        return result

    except Exception as e:
        logger.error(f"Error in async execution: {e}")
        raise
    finally:
        # Clean up the loop
        try:
            loop.close()
        except Exception:
            pass


@current_app.task(
    bind=True,
    max_retries=3,
    name="sync_job_task",
    priority=1,  # Highest priority for immediate execution
    queue="default",  # Explicitly specify default queue
    acks_late=False,  # Acknowledge immediately
    reject_on_worker_lost=False,  # Don't reject on worker restart
)
def sync_job_task(self, routing_id: str):
    """
    Sync a specific job routing to its target company.

    This task is enqueued by the OutboxWorker when processing JOB_SYNC events.
    It ensures that job routings are pushed to external providers (e.g., ServiceTitan)
    and updates the sync_status and external_id accordingly.
    """
    try:
        logger.info(
            "Starting job sync task",
            routing_id=routing_id,
            attempt=self.request.retries + 1,
            max_retries=self.max_retries,
        )

        # Import here to avoid circular imports
        from src.application.services.data_transformer import DataTransformer
        from src.application.services.provider_manager import ProviderManager
        from src.application.services.transaction_service import TransactionService
        from src.application.use_cases.sync_job import SyncJobUseCase
        from src.config.database import get_async_session_factory
        from src.infrastructure.database.repositories.company_repository import (
            CompanyRepository,
        )
        from src.infrastructure.database.repositories.job_repository import (
            JobRepository,
        )
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository,
        )
        from src.infrastructure.providers.factory import ProviderFactory

        async def execute_sync_with_transaction():
            """Execute sync operation within a transaction."""
            # Create session factory and session
            session_factory = get_async_session_factory()
            session = session_factory()
            transaction_service = TransactionService(session)

            try:
                # Create repositories with session
                job_routing_repo = JobRoutingRepository(session)
                job_repo = JobRepository(session)
                company_repo = CompanyRepository(session)
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
                    transaction_service=transaction_service,
                )

                # Convert string to UUID and execute
                routing_uuid = UUID(routing_id)
                result = await use_case.execute(routing_uuid)

                return result
            finally:
                if hasattr(session, "close"):
                    await session.close()

        # Execute with transaction using a new event loop
        result = run_async_in_new_loop(execute_sync_with_transaction())

        if result:
            logger.info(
                "Job sync task completed successfully",
                routing_id=routing_id,
                attempt=self.request.retries + 1,
                external_id=getattr(result, "external_id", None),
            )

            return {
                "status": "success",
                "routing_id": routing_id,
                "external_id": getattr(result, "external_id", None),
                "message": "Job successfully synced to external provider",
            }
        else:
            logger.warning(
                "Job sync task failed",
                routing_id=routing_id,
                attempt=self.request.retries + 1,
            )

            return {
                "status": "failed",
                "routing_id": routing_id,
                "reason": "Sync returned False",
            }

    except Exception as e:
        logger.error(
            "Job sync task failed with exception",
            routing_id=routing_id,
            error=str(e),
            error_type=type(e).__name__,
            attempt=self.request.retries + 1,
            max_retries=self.max_retries,
        )

        # Implement manual retry with exponential backoff
        if self.request.retries < self.max_retries:
            # Calculate delay with exponential backoff and jitter
            delay = (2**self.request.retries) + (random.random() * 0.1)

            logger.info(
                "Retrying job sync task",
                routing_id=routing_id,
                attempt=self.request.retries + 1,
                delay=delay,
            )

            # Retry the task
            raise self.retry(countdown=delay, max_retries=self.max_retries)
        else:
            logger.error(
                "Job sync task failed permanently after all retries",
                routing_id=routing_id,
                max_retries=self.max_retries,
            )

            return {
                "status": "failed_permanently",
                "routing_id": routing_id,
                "reason": f"Failed after {self.max_retries} retries: {str(e)}",
            }


@current_app.task(bind=True, max_retries=2, name="sync_pending_jobs_task")
def sync_pending_jobs_task(self):
    """
    BACKUP TASK: Find and sync pending job routings that were missed by OutboxWorker.

    This task runs every 2 minutes as a safety net to catch any jobs that:
    1. Failed to be processed by OutboxWorker
    2. Were created before OutboxWorker was running
    3. Have been stuck in 'pending' status for too long

    It should NOT duplicate the work of OutboxWorker.
    """
    try:
        logger.info(
            "Starting backup pending jobs sync task",
            attempt=self.request.retries + 1,
            max_retries=self.max_retries,
        )

        # Import here to avoid circular imports
        from src.application.services.provider_manager import ProviderManager
        from src.application.services.transaction_service import TransactionService
        from src.config.database import get_async_session_factory
        from src.infrastructure.database.repositories.company_repository import (
            CompanyRepository,
        )
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository,
        )
        from src.infrastructure.providers.factory import ProviderFactory

        async def execute_pending_sync_with_transaction():
            """Execute backup sync operation within a transaction."""
            # Create session factory and session
            session_factory = get_async_session_factory()
            session = session_factory()
            transaction_service = TransactionService(session)

            try:
                # Create repositories with session
                job_routing_repo = JobRoutingRepository(session)
                company_repo = CompanyRepository(session)
                provider_factory = ProviderFactory()
                provider_manager = ProviderManager(provider_factory, company_repo)

                stuck_routings = await job_routing_repo.find_stuck_pending_routings(
                    limit=20,  # Smaller batch for backup
                    older_than_minutes=5,  # Only process if stuck for 5+ minutes
                )

                if not stuck_routings:
                    logger.info("No stuck pending routings found for backup processing")
                    return {
                        "status": "success",
                        "message": "No stuck routings found",
                        "processed": 0,
                        "stuck_routings": [],
                        "task_type": "backup",
                    }

                logger.info(
                    "Found stuck routings for backup processing",
                    count=len(stuck_routings),
                    routing_ids=[str(r.id) for r in stuck_routings],
                )

                # Queue individual sync tasks for each stuck routing
                queued_count = 0
                queued_routing_ids = (
                    set()
                )  # Track queued routings to prevent duplicates

                for routing in stuck_routings:
                    try:
                        # Check if this routing is already queued
                        if str(routing.id) in queued_routing_ids:
                            logger.warning(
                                "Routing already queued in this batch - skipping duplicate",
                                routing_id=str(routing.id),
                            )
                            continue

                        # Mark as being processed by backup task
                        routing.mark_as_processing_by_backup()
                        await job_routing_repo.update(routing)
                        await transaction_service.commit()

                        # Queue sync task
                        sync_job_task.delay(str(routing.id))
                        queued_count += 1
                        queued_routing_ids.add(str(routing.id))

                        logger.info(
                            "Backup sync task queued for stuck routing",
                            routing_id=str(routing.id),
                            company_id=str(routing.company_id_received),
                            stuck_duration_minutes=routing.get_stuck_duration_minutes(),
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to queue backup sync task for stuck routing",
                            routing_id=str(routing.id),
                            error=str(e),
                        )
                        # Mark routing as failed since we couldn't queue it
                        await job_routing_repo.mark_sync_failed(
                            routing.id, f"Backup task failed to queue: {str(e)}"
                        )

                # Commit all changes
                await transaction_service.commit()

                return {
                    "status": "success",
                    "total_stuck": len(stuck_routings),
                    "queued_tasks": queued_count,
                    "stuck_routings": stuck_routings,
                    "task_type": "backup",
                }
            finally:
                if hasattr(session, "close"):
                    await session.close()

        # Execute with transaction using a new event loop
        result = run_async_in_new_loop(execute_pending_sync_with_transaction())

        logger.info(
            "Backup pending jobs sync task completed",
            total_stuck=result["total_stuck"],
            queued_tasks=result["queued_tasks"],
            task_type=result["task_type"],
            attempt=self.request.retries + 1,
        )

        return {
            "status": "success",
            "total_stuck": result["total_stuck"],
            "queued_tasks": result["queued_tasks"],
            "task_type": result["task_type"],
        }

    except Exception as e:
        logger.error(
            "Pending jobs sync task failed with exception",
            error=str(e),
            error_type=type(e).__name__,
            attempt=self.request.retries + 1,
            max_retries=self.max_retries,
        )

        # Implement manual retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_countdown = 120 * (2**self.request.retries)  # 2min, 4min
            logger.info(
                "Retrying pending jobs sync task",
                attempt=self.request.retries + 1,
                next_retry_in_seconds=retry_countdown,
            )
            raise self.retry(countdown=retry_countdown)

        # Max retries exceeded - log final failure
        logger.error(
            "Pending jobs sync task failed permanently after max retries",
            total_attempts=self.request.retries + 1,
            final_error=str(e),
        )

        return {
            "status": "permanently_failed",
            "error": str(e),
            "total_attempts": self.request.retries + 1,
        }


@current_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    name="poll_synced_jobs_task",
)
def poll_synced_jobs_task(self):
    """Poll for updates on synced jobs."""
    try:
        logger.info(
            "Starting synced jobs polling task", attempt=self.request.retries + 1
        )

        # Import here to avoid circular imports
        from src.application.services.provider_manager import ProviderManager
        from src.application.services.transaction_service import TransactionService
        from src.application.use_cases.poll_updates import PollUpdatesUseCase
        from src.config.database import get_async_session_factory
        from src.infrastructure.database.repositories.company_repository import (
            CompanyRepository,
        )
        from src.infrastructure.database.repositories.job_repository import (
            JobRepository,
        )
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository,
        )
        from src.infrastructure.providers.factory import ProviderFactory

        async def execute_poll_with_transaction():
            """Execute poll operation within a transaction."""
            # Create session and TransactionService
            session_factory = get_async_session_factory()
            session = session_factory()
            transaction_service = TransactionService(session)

            try:
                # Create repositories with session
                job_routing_repo = JobRoutingRepository(session)
                job_repo = JobRepository(session)
                company_repo = CompanyRepository(session)
                provider_factory = ProviderFactory()
                provider_manager = ProviderManager(provider_factory, company_repo)

                # Create and execute use case
                use_case = PollUpdatesUseCase(
                    job_routing_repo=job_routing_repo,
                    company_repo=company_repo,
                    job_repo=job_repo,
                    provider_manager=provider_manager,
                    transaction_service=transaction_service,  # Add missing parameter
                )

                result = await use_case.execute()
                return result
            finally:
                if hasattr(session, "close"):
                    await session.close()

        # Execute with transaction
        result = run_async_in_new_loop(execute_poll_with_transaction())

        logger.info(
            "Synced jobs polling task completed",
            jobs_checked=result.total_polled,
            jobs_updated=result.updated,
            jobs_completed=result.completed,
        )

        return {
            "status": "success",
            "jobs_checked": result.total_polled,
            "jobs_updated": result.updated,
            "jobs_completed": result.completed,
        }

    except Exception as e:
        logger.error(
            "Synced jobs polling task failed",
            error=str(e),
            attempt=self.request.retries + 1,
        )

        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2**self.request.retries))

        raise


@current_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    name="retry_failed_jobs_task",
)
def retry_failed_jobs_task(self):
    """Find and retry failed job routings."""
    try:
        logger.info("Starting failed jobs retry task", attempt=self.request.retries + 1)

        # Import here to avoid circular imports
        from src.application.services.transaction_service import TransactionService
        from src.config.database import get_async_session_factory
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository,
        )

        async def execute_retry_with_transaction():
            """Execute retry operation within a transaction."""
            # Create session factory and session
            session_factory = get_async_session_factory()
            session = session_factory()
            transaction_service = TransactionService(session)

            try:
                # Create repository with session
                job_routing_repo = JobRoutingRepository(session)

                # Find failed routings that should be retried
                failed_routings = await job_routing_repo.find_failed_for_retry(limit=25)

                if not failed_routings:
                    logger.info("No failed routings to retry")
                    return {
                        "status": "success",
                        "message": "No failed routings to retry",
                        "retried": 0,
                    }

                # Reset and queue retry for each failed routing
                retried_count = 0
                for routing in failed_routings:
                    try:
                        if routing.should_retry():
                            routing.reset_for_retry()
                            await job_routing_repo.update(routing)
                            await transaction_service.commit()

                            # Queue sync task
                            sync_job_task.delay(str(routing.id))
                            retried_count += 1

                            logger.info(
                                "Failed routing queued for retry",
                                routing_id=str(routing.id),
                                retry_count=routing.retry_count,
                            )

                    except Exception as e:
                        logger.error(
                            "Failed to retry routing",
                            routing_id=str(routing.id),
                            error=str(e),
                        )

                return {
                    "status": "success",
                    "total_failed": len(failed_routings),
                    "retried": retried_count,
                }
            finally:
                await transaction_service.commit()

        # Execute with transaction using a new event loop
        result = run_async_in_new_loop(execute_retry_with_transaction())

        logger.info(
            "Failed jobs retry task completed",
            total_failed=result["total_failed"],
            retried=result["retried"],
        )

        return {
            "status": "success",
            "total_failed": result["total_failed"],
            "retried": result["retried"],
        }

    except Exception as e:
        logger.error(
            "Failed jobs retry task failed",
            error=str(e),
            attempt=self.request.retries + 1,
        )

        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2**self.request.retries))

        raise


@current_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    name="retry_failed_job_task",
)
def retry_failed_job_task(self, routing_id: str):
    """Retry a specific failed job routing."""
    try:
        logger.info(
            "Starting individual job retry task",
            routing_id=routing_id,
            attempt=self.request.retries + 1,
        )

        # Import here to avoid circular imports
        from src.application.services.transaction_service import TransactionService
        from src.config.database import get_async_session_factory
        from src.infrastructure.database.repositories.job_routing_repository import (
            JobRoutingRepository,
        )

        async def execute_individual_retry_with_transaction():
            """Execute individual retry operation within a transaction."""
            # Create session and TransactionService
            session_factory = get_async_session_factory()
            session = session_factory()
            transaction_service = TransactionService(session)

            try:
                # Create repository with session
                job_routing_repo = JobRoutingRepository(session)

                # Get the routing
                routing_uuid = UUID(routing_id)
                routing = await job_routing_repo.get_by_id(routing_uuid)

                if not routing:
                    logger.error("Job routing not found", routing_id=routing_id)
                    return {"status": "error", "message": "Job routing not found"}

                # Check if it can be retried
                if not routing.should_retry():
                    logger.warning(
                        "Job routing cannot be retried",
                        routing_id=routing_id,
                        sync_status=routing.sync_status.value,
                        retry_count=routing.retry_count,
                    )
                    return {"status": "skipped", "message": "Cannot be retried"}

                # Reset for retry
                routing.reset_for_retry()
                await job_routing_repo.update(routing)

                # Queue sync task
                sync_job_task.delay(str(routing.id))

                return {
                    "status": "success",
                    "routing_id": routing_id,
                    "retry_count": routing.retry_count,
                }
            finally:
                if hasattr(session, "close"):
                    await session.close()

        # Execute with transaction
        result = run_async_in_new_loop(execute_individual_retry_with_transaction())

        logger.info(
            "Individual job retry task completed",
            routing_id=routing_id,
            retry_count=result.get("retry_count", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "Individual job retry task failed",
            routing_id=routing_id,
            error=str(e),
            attempt=self.request.retries + 1,
        )

        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2**self.request.retries))

        raise
