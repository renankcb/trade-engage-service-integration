"""
Repository interfaces for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.entities.company import Company
from src.domain.entities.job import Job
from src.domain.entities.job_routing import JobRouting
from src.domain.entities.technician import Technician
from src.domain.value_objects.sync_status import SyncStatus


class JobRoutingRepositoryInterface(ABC):
    """Job routing repository interface."""

    @abstractmethod
    async def create(self, job_routing: JobRouting) -> JobRouting:
        """Create a new job routing."""
        pass

    @abstractmethod
    async def get_by_id(self, job_routing_id: UUID) -> Optional[JobRouting]:
        """Get job routing by ID."""
        pass

    @abstractmethod
    async def get_by_job_id(self, job_id: UUID) -> List[JobRouting]:
        """Get all job routings for a specific job."""
        pass

    @abstractmethod
    async def find_by_status(
        self, status: SyncStatus, limit: int = 100
    ) -> List[JobRouting]:
        """Find job routings by sync status."""
        pass

    @abstractmethod
    async def find_pending_sync(self, limit: int = 50) -> List[JobRouting]:
        """Find job routings ready for sync."""
        pass

    @abstractmethod
    async def find_synced_for_polling(self, limit: int = 100) -> List[JobRouting]:
        """Find synced job routings that need status polling."""
        pass

    @abstractmethod
    async def update(self, job_routing: JobRouting) -> JobRouting:
        """Update job routing."""
        pass

    @abstractmethod
    async def delete(self, job_routing_id: UUID) -> bool:
        """Delete job routing."""
        pass


class CompanyRepositoryInterface(ABC):
    """Company repository interface."""

    @abstractmethod
    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        """Get company by ID."""
        pass

    @abstractmethod
    async def find_active_companies(self) -> List[Company]:
        """Find all active companies."""
        pass

    @abstractmethod
    async def find_active_by_provider_type(self) -> List[Company]:
        """Find all active companies that can receive jobs (have provider type)."""
        pass

    @abstractmethod
    async def find_active_with_skills_and_providers(self) -> List[dict]:
        """
        Find active companies with their skills and provider information.
        
        Returns:
            List of dictionaries containing company data with skills and provider info
            for intelligent job matching.
        """
        pass


class JobRepositoryInterface(ABC):
    """Job repository interface."""

    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> Optional[Job]:
        """Get job by ID."""
        pass

    @abstractmethod
    async def create(self, job: Job) -> Job:
        """Create a new job."""
        pass

    @abstractmethod
    async def update(self, job: Job) -> Job:
        """Update an existing job."""
        pass


class TechnicianRepositoryInterface(ABC):
    """Technician repository interface."""

    @abstractmethod
    async def get_by_id(self, technician_id: UUID) -> Optional[Technician]:
        """Get technician by ID."""
        pass

    @abstractmethod
    async def get_by_company_id(self, company_id: UUID) -> List[Technician]:
        """Get all technicians for a company."""
        pass

    @abstractmethod
    async def create(self, technician: Technician) -> Technician:
        """Create a new technician."""
        pass

    @abstractmethod
    async def update(self, technician: Technician) -> Technician:
        """Update an existing technician."""
        pass

    @abstractmethod
    async def delete(self, technician_id: UUID) -> bool:
        """Delete a technician."""
        pass
