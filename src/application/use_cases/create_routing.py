"""Create job routing use case."""

from uuid import UUID

from src.application.interfaces.repositories import (
    CompanyRepositoryInterface,
    JobRepositoryInterface,
    JobRoutingRepositoryInterface,
)
from src.config.logging import get_logger
from src.domain.entities.job_routing import JobRouting
from src.domain.exceptions.validation_error import ValidationError

logger = get_logger(__name__)


class CreateJobRoutingUseCase:
    """Use case for creating job routing."""

    def __init__(
        self,
        job_routing_repo: JobRoutingRepositoryInterface,
        job_repo: JobRepositoryInterface,
        company_repo: CompanyRepositoryInterface,
    ):
        self.job_routing_repo = job_routing_repo
        self.job_repo = job_repo
        self.company_repo = company_repo

    async def execute(self, job_id: UUID, company_id: UUID) -> JobRouting:
        """Create new job routing."""
        # 1. Validate job exists
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found")

        if not job.can_be_routed():
            raise ValidationError("Job cannot be routed - missing required fields")

        # 2. Validate company exists and can receive jobs
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise ValidationError(f"Company {company_id} not found")

        if not company.can_receive_jobs():
            raise ValidationError(f"Company {company.name} cannot receive jobs")

        # 3. Check for existing routing
        existing_routings = await self.job_routing_repo.get_by_job_id(job_id)
        for routing in existing_routings:
            if routing.company_id_received == company_id:
                raise ValidationError("Job already routed to this company")

        # 4. Create job routing
        job_routing = JobRouting(job_id=job_id, company_id_received=company_id)

        created_routing = await self.job_routing_repo.create(job_routing)

        logger.info(
            "Job routing created",
            job_routing_id=str(created_routing.id),
            job_id=str(job_id),
            company_id=str(company_id),
            company_name=company.name,
        )

        return created_routing
