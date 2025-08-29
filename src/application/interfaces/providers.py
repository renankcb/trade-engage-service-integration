"""
Provider interfaces for dependency inversion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.domain.entities.job import Job


@dataclass
class CreateLeadRequest:
    """Request to create lead in provider system."""

    job: Job
    company_config: Dict[str, Any]
    idempotency_key: str  # Unique key to prevent duplicates (e.g., job_routing_id)


@dataclass
class CreateLeadResponse:
    """Response from creating lead in provider system."""

    success: bool
    external_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class JobStatusResponse:
    """Response from provider job status check."""

    external_id: str
    status: str
    is_completed: bool
    revenue: Optional[float] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ProviderHealthStatus:
    """Provider health status information."""

    is_healthy: bool
    status_message: str
    last_check: str
    response_time_ms: Optional[float] = None
    error_details: Optional[str] = None


class ProviderInterface(ABC):
    """Base interface for all POS providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def create_lead(self, request: CreateLeadRequest) -> CreateLeadResponse:
        """Create a lead/job in the provider system."""
        pass

    @abstractmethod
    async def get_job_status(
        self, external_id: str, config: Dict[str, Any]
    ) -> JobStatusResponse:
        """Get status of a specific job."""
        pass

    @abstractmethod
    async def batch_get_job_status(
        self, external_ids: List[str], config: Dict[str, Any]
    ) -> List[JobStatusResponse]:
        """Get status of multiple jobs in batch."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate provider configuration."""
        pass
