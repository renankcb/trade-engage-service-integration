"""
Mock provider for testing and development.
"""

import asyncio
from typing import Any, Dict, List
from uuid import uuid4

from src.application.interfaces.providers import (
    CreateLeadRequest,
    CreateLeadResponse,
    JobStatusResponse,
    ProviderInterface,
)
from src.config.logging import get_logger

logger = get_logger(__name__)


class MockProvider(ProviderInterface):
    """Mock provider implementation for testing."""

    def __init__(self):
        self._jobs_store: Dict[str, Dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "Mock Provider"

    async def create_lead(self, request: CreateLeadRequest) -> CreateLeadResponse:
        """Create a mock lead."""
        # Simulate API delay
        await asyncio.sleep(0.1)

        # Generate mock external ID
        external_id = f"mock_{uuid4().hex[:8]}"

        # Store job in mock database
        self._jobs_store[external_id] = {
            "id": external_id,
            "summary": request.job.summary,
            "status": "scheduled",
            "is_completed": False,
            "created_at": "2024-01-01T00:00:00Z",
            "revenue": None,
        }

        logger.info("Mock lead created", external_id=external_id)

        return CreateLeadResponse(success=True, external_id=external_id)

    async def get_job_status(
        self, external_id: str, config: Dict[str, Any]
    ) -> JobStatusResponse:
        """Get mock job status."""
        # Simulate API delay
        await asyncio.sleep(0.1)

        job_data = self._jobs_store.get(external_id)

        if not job_data:
            return JobStatusResponse(
                external_id=external_id,
                status="not_found",
                is_completed=False,
                error_message=(
                    "Job not found in mock system"
                ),
            )

        # Simulate job progression (10% chance to complete)
        import random

        if not job_data["is_completed"] and random.random() < 0.1:
            job_data["status"] = "completed"
            job_data["is_completed"] = True
            job_data["revenue"] = random.uniform(100.0, 500.0)
            job_data["completed_at"] = "2024-01-01T12:00:00Z"

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

        logger.info("Mock batch status retrieved", count=len(results))
        return results

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate mock provider config (always valid)."""
        return True
