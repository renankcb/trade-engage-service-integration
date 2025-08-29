"""Poll updates use case for checking job completion status."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from src.application.interfaces.repositories import (
    CompanyRepositoryInterface,
    JobRepositoryInterface,
    JobRoutingRepositoryInterface,
)
from src.application.services.provider_manager import ProviderManager
from src.application.services.transaction_service import TransactionService
from src.config.logging import get_logger
from src.config.settings import settings
from src.domain.entities.job_routing import JobRouting
from src.domain.value_objects.provider_type import ProviderType
from src.domain.value_objects.sync_status import SyncStatus

logger = get_logger(__name__)


@dataclass
class PollResult:
    """Result of polling operation."""

    total_polled: int
    updated: int
    completed: int
    errors: List[str]
    processing_time: float


class PollUpdatesUseCase:
    """Use case for polling provider APIs for job status updates."""

    def __init__(
        self,
        job_routing_repo: JobRoutingRepositoryInterface,
        company_repo: CompanyRepositoryInterface,
        job_repo: JobRepositoryInterface,
        provider_manager: ProviderManager,
        transaction_service: TransactionService,
    ):
        self.job_routing_repo = job_routing_repo
        self.company_repo = company_repo
        self.job_repo = job_repo
        self.provider_manager = provider_manager
        self.transaction_service = transaction_service

    async def execute(self, limit: int = None) -> PollResult:
        """Execute polling for synced job statuses."""
        start_time = datetime.now(timezone.utc)
        poll_limit = limit or settings.POLLING_BATCH_SIZE

        logger.info("Starting job status polling", limit=poll_limit)

        # Get synced jobs that need polling
        synced_routings = await self.job_routing_repo.find_synced_for_polling(
            poll_limit
        )

        if not synced_routings:
            logger.info("No synced jobs found for polling")
            return PollResult(
                total_polled=0, updated=0, completed=0, errors=[], processing_time=0.0
            )

        # Group by provider and company for efficient batch calls
        grouped_routings = await self._group_by_provider_and_company(synced_routings)

        total_polled = 0
        updated = 0
        completed = 0
        errors = []

        # Process each provider/company group
        for (provider_type, company_id), routings in grouped_routings.items():
            try:
                group_result = await self._poll_provider_group(
                    provider_type, company_id, routings
                )

                total_polled += group_result.total_polled
                updated += group_result.updated
                completed += group_result.completed
                errors.extend(group_result.errors)

            except Exception as e:
                error_msg = f"Provider {provider_type.value} polling failed: {str(e)}"
                logger.error(
                    "Provider polling failed",
                    provider=provider_type.value,
                    error=str(e),
                )
                errors.append(error_msg)

        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = PollResult(
            total_polled=total_polled,
            updated=updated,
            completed=completed,
            errors=errors,
            processing_time=processing_time,
        )

        logger.info(
            "Job status polling completed",
            total=total_polled,
            updated=updated,
            completed=completed,
            errors=len(errors),
            duration=f"{processing_time:.2f}s",
        )

        return result

    async def _group_by_provider_and_company(
        self, routings: List[JobRouting]
    ) -> Dict[tuple, List[JobRouting]]:
        """Group routings by provider type and company for batch processing."""
        grouped = {}

        # Load company data for each routing
        for routing in routings:
            company = await self.company_repo.get_by_id(routing.company_id_received)
            if not company:
                continue

            key = (company.provider_type, company.id)

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(routing)

        return grouped

    async def _poll_provider_group(
        self, provider_type: ProviderType, company_id: str, routings: List[JobRouting]
    ) -> PollResult:
        """Poll status for a group of jobs from same provider/company."""
        start_time = datetime.now(timezone.utc)

        logger.info(
            "Polling provider group",
            provider=provider_type.value,
            company_id=str(company_id),
            count=len(routings),
        )

        updated = 0
        completed = 0
        errors = []

        try:
            # Get provider and company config
            company = await self.company_repo.get_by_id(company_id)

            if not company:
                error_msg = f"Company {company_id} not found"
                errors.append(error_msg)
                return PollResult(len(routings), 0, 0, [error_msg], 0.0)

            provider = self.provider_manager.get_provider(
                provider_type, company=company
            )

            # Extract external IDs for batch polling
            external_ids = [r.external_id for r in routings if r.external_id]

            if not external_ids:
                logger.warning("No external IDs found for polling", count=len(routings))
                return PollResult(len(routings), 0, 0, [], 0.0)

            # Batch poll provider API
            status_responses = await provider.batch_get_job_status(
                external_ids, company.provider_config
            )

            # Create lookup map
            status_map = {resp.external_id: resp for resp in status_responses}

            # Update each routing based on response
            for routing in routings:
                try:
                    if not routing.external_id:
                        continue

                    status_resp = status_map.get(routing.external_id)
                    if not status_resp:
                        errors.append(f"No status response for {routing.external_id}")
                        continue

                    if status_resp.error_message:
                        errors.append(
                            f"Status error for {routing.external_id}: {status_resp.error_message}"
                        )
                        continue

                    # Check if job is completed
                    if (
                        status_resp.is_completed
                        and routing.sync_status == SyncStatus.SYNCED
                    ):
                        # Update job routing
                        routing.mark_completed()
                        completed += 1
                        updated += 1

                        # Update job entity with completion data
                        job = await self.job_repo.get_by_id(routing.job_id)
                        if job and status_resp.revenue:
                            job.mark_completed(
                                status_resp.revenue, status_resp.completed_at
                            )
                            await self.job_repo.update(job)

                        logger.info(
                            "Job marked as completed",
                            routing_id=str(routing.id),
                            external_id=routing.external_id,
                            revenue=status_resp.revenue,
                        )
                    else:
                        # Update last polled time even if not completed
                        routing.last_synced_at = datetime.now(timezone.utc)
                        updated += 1

                    await self.job_routing_repo.update(routing)

                    await self.transaction_service.commit()

                except Exception as e:
                    error_msg = f"Failed to update routing {routing.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(
                        "Routing update failed",
                        routing_id=str(routing.id),
                        error=str(e),
                    )

            # Commit all changes atomically
            if updated > 0 or completed > 0:
                logger.info(
                    "Transaction committed successfully",
                    provider=provider_type.value,
                    company_id=str(company_id),
                    updated=updated,
                    completed=completed,
                )

        except Exception as e:
            error_msg = f"Provider polling failed: {str(e)}"
            errors.append(error_msg)
            logger.error(
                "Provider group polling failed",
                provider=provider_type.value,
                error=str(e),
            )

        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        return PollResult(
            total_polled=len(routings),
            updated=updated,
            completed=completed,
            errors=errors,
            processing_time=processing_time,
        )

    def _should_poll(self, routing: JobRouting) -> bool:
        """Determine if routing should be polled based on timing rules."""
        if routing.sync_status != SyncStatus.SYNCED:
            return False

        # Don't poll too frequently
        if routing.last_synced_at:
            time_since_last_poll = datetime.now(timezone.utc) - routing.last_synced_at
            min_interval = timedelta(minutes=settings.SYNC_INTERVAL_MINUTES)

            if time_since_last_poll < min_interval:
                return False

        return True
