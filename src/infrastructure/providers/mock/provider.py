"""
Mock provider for testing and development.
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from src.application.interfaces.providers import (
    CreateLeadRequest,
    CreateLeadResponse,
    JobStatusResponse,
    ProviderInterface,
)
from src.config.logging import get_logger
from src.domain.entities.company import Company
from src.infrastructure.providers.mock.data_store import mock_data_store

logger = get_logger(__name__)


class MockProvider(ProviderInterface):
    """Mock provider implementation for testing."""

    def __init__(self, company: Company):
        self.company = company
        # Use Redis-based data store for cross-process persistence
        self.data_store = mock_data_store
        logger.info(
            "MockProvider initialized",
            company_id=str(company.id),
            provider_type=company.provider_type.value,
            data_store_type="redis",
        )

    @property
    def name(self) -> str:
        return "Mock Provider"

    async def create_lead(self, request: CreateLeadRequest) -> CreateLeadResponse:
        """Create a mock lead."""
        # Simulate API delay
        await asyncio.sleep(0.1)

        # Generate mock external ID
        external_id = f"mock_{uuid4().hex[:8]}"

        # Store job in global mock data store
        job_data = {
            "id": external_id,
            "summary": request.job.summary,
            "status": "pending",  # Start as pending, not completed
            "is_completed": False,  # Start as not completed
            "created_at": datetime.now(timezone.utc).isoformat(),
            "revenue": None,  # No revenue yet
            "completed_at": None,  # Not completed yet
            "company_id": str(self.company.id),
            "provider_type": self.company.provider_type.value,
        }

        await self.data_store.store_job(external_id, job_data)

        logger.info(
            "Mock lead created successfully",
            external_id=external_id,
            status="pending",
            company_id=str(self.company.id),
        )

        return CreateLeadResponse(success=True, external_id=external_id)

    async def get_job_status(
        self, external_id: str, config: Dict[str, Any]
    ) -> JobStatusResponse:
        """Get mock job status."""
        # Simulate API delay
        await asyncio.sleep(0.1)

        logger.info(
            "Getting job status from mock provider",
            external_id=external_id,
            company_id=str(self.company.id),
            data_store_type="redis",
        )

        # Get job from global data store
        job_data = await self.data_store.get_job(external_id)

        if not job_data:
            # Get available jobs for debugging
            available_jobs = await self.data_store.list_jobs()
            logger.warning(
                "Job not found in mock data store",
                external_id=external_id,
                available_jobs=available_jobs,
                store_size=len(available_jobs),
            )
            return JobStatusResponse(
                external_id=external_id,
                status="not_found",
                is_completed=False,
                error_message="Job not found in mock system",
            )

        logger.info(
            "Job found in mock data store",
            external_id=external_id,
            current_status=job_data["status"],
            is_completed=job_data["is_completed"],
        )

        # Simulate job progression (20% chance to complete for pending jobs)
        if not job_data["is_completed"] and random.random() < 0.2:
            # Mark as completed
            job_data["status"] = "completed"
            job_data["is_completed"] = True
            job_data["revenue"] = random.uniform(100.0, 500.0)
            job_data["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Update in store
            await self.data_store.update_job(external_id, job_data)

            logger.info(
                "Mock job marked as completed",
                external_id=external_id,
                revenue=job_data["revenue"],
            )
        elif not job_data["is_completed"]:
            # Simulate other statuses for non-completed jobs
            if random.random() < 0.3:
                new_status = "in_progress"
            elif random.random() < 0.5:
                new_status = "scheduled"
            else:
                new_status = "pending"

            if new_status != job_data["status"]:
                job_data["status"] = new_status
                await self.data_store.update_job(external_id, {"status": new_status})
                logger.info(
                    "Mock job status updated",
                    external_id=external_id,
                    new_status=new_status,
                )

        return JobStatusResponse(
            external_id=external_id,
            status=job_data["status"],
            is_completed=job_data["is_completed"],
            revenue=job_data.get("revenue"),
            completed_at=job_data.get("completed_at"),
        )

    async def batch_get_job_status(
        self, external_ids: List[str], config: Dict[str, Any]
    ) -> List[JobStatusResponse]:
        """Get multiple mock job statuses."""
        # Simulate batch API delay
        await asyncio.sleep(0.2)

        results = []
        for external_id in external_ids:
            status = await self.get_job_status(external_id, config)
            results.append(status)

        logger.info(
            "Mock batch status retrieved", count=len(results), external_ids=external_ids
        )
        return results

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate mock provider config (always valid)."""
        return True

    async def get_store_stats(self) -> Dict[str, Any]:
        """Get statistics about the mock data store (for debugging)."""
        return await self.data_store.get_stats()
