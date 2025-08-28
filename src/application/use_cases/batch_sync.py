"""Batch sync use case for processing multiple jobs efficiently."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
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
from src.config.settings import settings
from src.domain.entities.job_routing import JobRouting
from src.domain.value_objects.provider_type import ProviderType
from src.domain.value_objects.sync_status import SyncStatus

logger = get_logger(__name__)


@dataclass
class BatchSyncResult:
    """Result of batch sync operation."""

    total_processed: int
    successful: int
    failed: int
    skipped: int
    errors: List[str]
    processing_time: float


class BatchSyncUseCase:
    """Use case for batch processing multiple job syncs."""

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

    async def execute(self, limit: int = None) -> BatchSyncResult:
        """Execute batch sync of pending jobs."""
        start_time = datetime.utcnow()
        batch_size = limit or settings.BATCH_SIZE

        logger.info("Starting batch sync", batch_size=batch_size)

        # Get pending jobs
        pending_routings = await self.job_routing_repo.find_pending_sync(batch_size)

        if not pending_routings:
            logger.info("No pending job routings found")
            return BatchSyncResult(
                total_processed=0,
                successful=0,
                failed=0,
                skipped=0,
                errors=[],
                processing_time=0.0,
            )

        # Group by provider for efficient processing
        grouped_routings = self._group_by_provider(pending_routings)

        total_processed = 0
        successful = 0
        failed = 0
        skipped = 0
        errors = []

        # Process each provider group
        for provider_type, routings in grouped_routings.items():
            try:
                provider_result = await self._process_provider_batch(
                    provider_type, routings
                )

                total_processed += provider_result.total_processed
                successful += provider_result.successful
                failed += provider_result.failed
                skipped += provider_result.skipped
                errors.extend(provider_result.errors)

            except Exception as e:
                error_msg = f"Provider {provider_type.value} batch failed: {str(e)}"
                logger.error(
                    "Provider batch processing failed",
                    provider=provider_type.value,
                    error=str(e),
                )
                errors.append(error_msg)
                failed += len(routings)

        # Calculate metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Record metrics
        # MetricsCollector.record_background_task("batch_sync", successful > failed) # Removed MetricsCollector

        result = BatchSyncResult(
            total_processed=total_processed,
            successful=successful,
            failed=failed,
            skipped=skipped,
            errors=errors,
            processing_time=processing_time,
        )

        logger.info(
            "Batch sync completed",
            total=total_processed,
            successful=successful,
            failed=failed,
            skipped=skipped,
            duration=f"{processing_time:.2f}s",
        )

        return result

    def _group_by_provider(
        self, routings: List[JobRouting]
    ) -> Dict[ProviderType, List[JobRouting]]:
        """Group job routings by provider type."""
        grouped = {}

        # We need to load company data to get provider types
        # This is simplified - in real implementation, we'd do this more efficiently
        for routing in routings:
            # For now, assume we have a way to determine provider type
            # In practice, this would require joining with companies table
            provider_type = ProviderType.MOCK  # Placeholder

            if provider_type not in grouped:
                grouped[provider_type] = []
            grouped[provider_type].append(routing)

        return grouped

    async def _process_provider_batch(
        self, provider_type: ProviderType, routings: List[JobRouting]
    ) -> BatchSyncResult:
        """Process batch for specific provider."""
        start_time = datetime.utcnow()

        logger.info(
            "Processing provider batch",
            provider=provider_type.value,
            count=len(routings),
        )

        successful = 0
        failed = 0
        skipped = 0
        errors = []

        try:
            provider = self.provider_manager.get_provider(provider_type)

            # Process routings individually (could be optimized for true batch operations)
            for routing in routings:
                try:
                    # Validate routing can be processed
                    if not routing.can_sync():
                        skipped += 1
                        continue

                    # Load job and company data
                    job = await self.job_repo.get_by_id(routing.job_id)
                    company = await self.company_repo.get_by_id(
                        routing.company_id_received
                    )

                    if not job or not company:
                        errors.append(f"Missing data for routing {routing.id}")
                        failed += 1
                        continue

                    # Mark sync started
                    routing.mark_sync_started()
                    await self.job_routing_repo.update(routing)

                    # Create lead
                    request = CreateLeadRequest(
                        job=job, company_config=company.provider_config
                    )

                    response = await provider.create_lead(request)

                    # Handle response
                    if response.success and response.external_id:
                        routing.mark_sync_success(response.external_id)
                        successful += 1
                    else:
                        error_msg = response.error_message or "Unknown provider error"
                        routing.mark_sync_failed(error_msg)
                        errors.append(f"Routing {routing.id}: {error_msg}")
                        failed += 1

                    await self.job_routing_repo.update(routing)

                    # Record individual metrics
                    # MetricsCollector.record_job_sync( # Removed MetricsCollector
                    #     provider_type.value,
                    #     response.success,
                    #     0.0,  # Duration would be calculated if needed
                    # )

                except Exception as e:
                    error_msg = f"Routing {routing.id} failed: {str(e)}"
                    errors.append(error_msg)
                    failed += 1

                    # Mark routing as failed
                    try:
                        routing.mark_sync_failed(str(e))
                        await self.job_routing_repo.update(routing)
                    except:
                        pass  # Don't fail batch due to update error

        except Exception as e:
            # Provider-level error
            error_msg = f"Provider {provider_type.value} batch error: {str(e)}"
            errors.append(error_msg)
            failed += len(routings)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return BatchSyncResult(
            total_processed=len(routings),
            successful=successful,
            failed=failed,
            skipped=skipped,
            errors=errors,
            processing_time=processing_time,
        )
