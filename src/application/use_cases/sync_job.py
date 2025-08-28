"""Sync job use case implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from src.application.interfaces.providers import CreateLeadRequest
from src.application.interfaces.repositories import (
    CompanyRepositoryInterface,
    JobRepositoryInterface,
    JobRoutingRepositoryInterface,
)
from src.application.services.data_transformer import DataTransformer
from src.application.services.provider_manager import ProviderManager
from src.config.logging import get_logger
from src.domain.entities.job_routing import JobRouting
from src.domain.exceptions.sync_error import SyncError, SyncStatusError

logger = get_logger(__name__)


class SyncJobUseCase:
    """Use case for syncing a job to external provider."""

    def __init__(
        self,
        job_routing_repo: JobRoutingRepositoryInterface,
        job_repo: JobRepositoryInterface,
        company_repo: CompanyRepositoryInterface,
        provider_manager: ProviderManager,
        data_transformer: DataTransformer,
    ):
        self.job_routing_repo = job_routing_repo
        self.job_repo = job_repo
        self.company_repo = company_repo
        self.provider_manager = provider_manager
        self.data_transformer = data_transformer

    async def execute(self, job_routing_id: UUID) -> bool:
        """Execute job sync to external provider."""
        try:
            # 1. Load job routing
            job_routing = await self.job_routing_repo.get_by_id(job_routing_id)
            if not job_routing:
                raise SyncError(f"Job routing {job_routing_id} not found")

            # 2. Validate sync can proceed
            if not job_routing.can_sync():
                raise SyncStatusError(
                    str(job_routing.sync_status),
                    "pending or failed with retries available",
                )

            # 3. Load related data
            job = await self.job_repo.get_by_id(job_routing.job_id)
            if not job:
                raise SyncError(f"Job {job_routing.job_id} not found")

            company = await self.company_repo.get_by_id(job_routing.company_id_received)
            if not company:
                raise SyncError(f"Company {job_routing.company_id_received} not found")

            # 4. Mark sync started
            job_routing.mark_sync_started()
            await self.job_routing_repo.update(job_routing)

            logger.info(
                "Job sync started",
                job_routing_id=str(job_routing_id),
                job_id=str(job.id),
                company=company.name,
                provider=company.provider_type.value,
            )

            # 5. Get provider and create lead
            provider = self.provider_manager.get_provider(company.provider_type)

            # Create request with idempotency key to prevent duplicates
            request = CreateLeadRequest(
                job=job, 
                company_config=company.provider_config,
                idempotency_key=str(job_routing.id)  # Use routing ID as idempotency key
            )

            response = await provider.create_lead(request)

            # 6. Handle response
            if response.success and response.external_id:
                job_routing.mark_sync_success(response.external_id)
                await self.job_routing_repo.update(job_routing)

                logger.info(
                    "Job sync successful",
                    job_routing_id=str(job_routing_id),
                    external_id=response.external_id,
                    provider=company.provider_type.value,
                )
                return True
            else:
                error_msg = response.error_message or "Unknown provider error"
                job_routing.mark_sync_failed(error_msg)
                await self.job_routing_repo.update(job_routing)

                logger.error(
                    "Job sync failed",
                    job_routing_id=str(job_routing_id),
                    error=error_msg,
                    provider=company.provider_type.value,
                )
                return False

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Sync failed with exception: {str(e)}"

            try:
                job_routing = await self.job_routing_repo.get_by_id(job_routing_id)
                if job_routing:
                    job_routing.mark_sync_failed(error_msg)
                    await self.job_routing_repo.update(job_routing)
            except Exception as update_error:
                logger.error(
                    "Failed to update job routing after error", error=str(update_error)
                )

            logger.error(
                "Job sync exception",
                job_routing_id=str(job_routing_id),
                error=str(e),
                exc_info=True,
            )

            return False
