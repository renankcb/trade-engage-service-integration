"""
Celery tasks for job synchronization.
"""

import asyncio
import random
from uuid import UUID

import structlog
from celery import current_app

logger = structlog.get_logger()


@current_app.task(bind=True, max_retries=3, name="sync_job_task")
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
                await session.close()

        # Execute with transaction using a new event loop
        import asyncio

        try:
            # Create a new event loop for this task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(execute_sync_with_transaction())
        finally:
            loop.close()

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
    """Find and sync all pending job routings."""
    try:
        logger.info(
            "Starting pending jobs sync task",
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
            """Execute pending sync operation within a transaction."""
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

                # IMPLEMENTAR CLAIM PATTERN para evitar duplicatas
                # Buscar e marcar routings como 'processing' atomicamente
                claimed_routings = await job_routing_repo.claim_pending_routings(
                    limit=50
                )

                if not claimed_routings:
                    logger.info("No pending routings available for claiming")
                    return {
                        "status": "success",
                        "message": "No pending routings available",
                        "processed": 0,
                        "claimed_routings": [],
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
                            claim_timestamp=routing.claimed_at,
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to queue sync task for claimed routing",
                            routing_id=str(routing.id),
                            error=str(e),
                        )
                        # Mark routing as failed since we couldn't queue it
                        await job_routing_repo.mark_sync_failed(
                            routing.id, f"Failed to queue sync task: {str(e)}"
                        )

                return {
                    "status": "success",
                    "total_claimed": len(claimed_routings),
                    "queued_tasks": queued_count,
                    "claimed_routings": claimed_routings,
                }
            finally:
                await session.close()

        # Execute with transaction using a new event loop
        import asyncio

        try:
            # Create a new event loop for this task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(execute_pending_sync_with_transaction())
        finally:
            loop.close()

        logger.info(
            "Pending jobs sync task completed",
            total_claimed=result["total_claimed"],
            queued_tasks=result["queued_tasks"],
            attempt=self.request.retries + 1,
        )

        return {
            "status": "success",
            "total_claimed": result["total_claimed"],
            "queued_tasks": result["queued_tasks"],
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
            session = get_async_session_factory()
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
                )

                result = await use_case.execute()
                return result
            finally:
                await session.close()

        # Execute with transaction
        result = asyncio.run(execute_poll_with_transaction())

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
        import asyncio

        try:
            # Create a new event loop for this task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(execute_retry_with_transaction())
        finally:
            loop.close()

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
            session = get_async_session_factory()
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
                await session.close()

        # Execute with transaction
        result = asyncio.run(execute_individual_retry_with_transaction())

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
