"""Create job use case."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from src.application.interfaces.repositories import (
    CompanyRepositoryInterface,
    JobRepositoryInterface,
    JobRoutingRepositoryInterface,
    TechnicianRepositoryInterface,
)
from src.application.services.job_matching_engine import (
    JobMatchingEngine,
    JobRequirements,
)
from src.config.logging import get_logger
from src.domain.entities.job import Job
from src.domain.entities.job_routing import JobRouting
from src.domain.exceptions.validation_error import ValidationError
from src.domain.value_objects.address import Address
from src.domain.value_objects.homeowner import Homeowner
from src.infrastructure.database.repositories.transaction_repository import (
    TransactionService,
)
from src.infrastructure.database.repositories.transactional_outbox_repository import (
    OutboxEventType,
    TransactionalOutbox,
)

logger = get_logger(__name__)


@dataclass
class CreateJobRequest:
    """Request for creating a job."""

    summary: str
    address: Address
    homeowner: Homeowner
    created_by_company_id: UUID
    created_by_technician_id: UUID
    required_skills: List[str] = None  # Skills required for this job
    skill_levels: dict = None  # skill_name -> required_level mapping
    category: str = None  # Job category for classification


@dataclass
class CreateJobResult:
    """Result of job creation."""

    job: Job
    routing: JobRouting  # Single routing for the best matching company
    matching_score: float  # Matching quality score for the selected company


class CreateJobUseCase:
    """Use case for creating a job and routing it to the best matching company."""

    def __init__(
        self,
        job_repo: JobRepositoryInterface,
        company_repo: CompanyRepositoryInterface,
        technician_repo: TechnicianRepositoryInterface,
        job_routing_repo: JobRoutingRepositoryInterface,
        matching_engine: JobMatchingEngine,
        outbox: TransactionalOutbox,
        transaction_service: TransactionService,
    ):
        self.job_repo = job_repo
        self.company_repo = company_repo
        self.technician_repo = technician_repo
        self.job_routing_repo = job_routing_repo
        self.matching_engine = matching_engine
        self.outbox = outbox
        self.transaction_service = transaction_service

    async def execute(self, request: CreateJobRequest) -> CreateJobResult:
        """Create a new job and route it to the best matching company using intelligent matching."""

        logger.info(
            "Starting job creation with intelligent matching",
            summary=request.summary,
            category=request.category,
            required_skills=request.required_skills,
            created_by_company_id=str(request.created_by_company_id),
            created_by_technician_id=str(request.created_by_technician_id),
        )

        # 1. Validate requesting company exists
        requesting_company = await self.company_repo.get_by_id(
            request.created_by_company_id
        )
        if not requesting_company:
            raise ValidationError(
                f"Requesting company {request.created_by_company_id} not found"
            )

        # 2. Validate identifying technician exists and belongs to requesting company
        identifying_technician = await self.technician_repo.get_by_id(
            request.created_by_technician_id
        )
        if not identifying_technician:
            raise ValidationError(
                f"Identifying technician {request.created_by_technician_id} not found"
            )

        if identifying_technician.company_id != request.created_by_company_id:
            raise ValidationError(
                "Identifying technician does not belong to the requesting company"
            )

        # 3. Validate skills and category (if provided)
        if request.required_skills:
            if not isinstance(request.required_skills, list):
                raise ValidationError("Required skills must be a list")
            if not all(
                isinstance(skill, str) and skill.strip()
                for skill in request.required_skills
            ):
                raise ValidationError("All required skills must be non-empty strings")

        if request.skill_levels:
            if not isinstance(request.skill_levels, dict):
                raise ValidationError("Skill levels must be a dictionary")
            valid_levels = {"basic", "intermediate", "expert"}
            for skill, level in request.skill_levels.items():
                if level not in valid_levels:
                    raise ValidationError(
                        f"Invalid skill level '{level}' for skill '{skill}'. Must be one of: {valid_levels}"
                    )

        job_requirements = JobRequirements(
            job_id=UUID("00000000-0000-0000-0000-000000000000"),
            required_skills=request.required_skills or [],
            skill_levels=request.skill_levels or {},
            location={
                "street": request.address.street,
                "city": request.address.city,
                "state": request.address.state,
                "zip_code": request.address.zip_code,
            },
        )

        # Get available companies with their skills and provider info
        available_companies = (
            await self.company_repo.find_active_with_skills_and_providers()
        )

        if not available_companies:
            raise ValidationError(
                "No active companies with provider configuration found"
            )

        # Use matching engine to find the BEST company
        best_company_match = await self.matching_engine.find_matching_company(
            job_requirements,
            available_companies,
            exclude_company_id=request.created_by_company_id,
        )

        if not best_company_match:
            raise ValidationError(
                f"No suitable companies found for job requirements. "
                f"Required skills: {request.required_skills or 'None'}, "
                f"Category: {request.category or 'None'}"
            )

        logger.info(
            "Found best matching company for job",
            total_companies=len(available_companies),
            selected_company_id=str(best_company_match.company_id),
            matching_score=best_company_match.score,
            matched_skills=best_company_match.matched_skills,
            provider_type=best_company_match.provider_type,
        )

        try:
            # 5.1. Create the job with skills and category
            job = Job(
                summary=request.summary,
                address=request.address,
                homeowner_name=request.homeowner.name,
                homeowner_phone=request.homeowner.phone,
                homeowner_email=request.homeowner.email,
                created_by_company_id=request.created_by_company_id,
                created_by_technician_id=request.created_by_technician_id,
                required_skills=request.required_skills,
                skill_levels=request.skill_levels,
            )

            # 5.2. Persist the job
            created_job = await self.job_repo.create(job)

            # 5.3. Create and persist routing for the BEST matching company
            routing = JobRouting(
                job_id=created_job.id,
                company_id_received=best_company_match.company_id,
                sync_status="pending",
            )

            persisted_routing = await self.job_routing_repo.create(routing)

            # 5.4. Create outbox event for immediate sync (atomic operation)
            await self.outbox.create_event(
                event_type=OutboxEventType.JOB_SYNC,
                aggregate_id=str(persisted_routing.id),
                event_data={
                    "routing_id": str(persisted_routing.id),
                    "job_id": str(created_job.id),
                    "company_id": str(best_company_match.company_id),
                    "matching_score": best_company_match.score,
                    "matched_skills": best_company_match.matched_skills,
                    "provider_type": best_company_match.provider_type,
                },
            )

            logger.debug(
                "Created routing and outbox event for best matching company",
                routing_id=str(persisted_routing.id),
                company_id=str(best_company_match.company_id),
                matching_score=best_company_match.score,
                matched_skills=best_company_match.matched_skills,
            )

            await self.transaction_service.commit()

            logger.info(
                "Transaction committed successfully - job, routing, and outbox event persisted",
                job_id=str(created_job.id),
                routing_id=str(persisted_routing.id),
            )

        except Exception as e:
            logger.error(
                "Failed to create job and routing - transaction will be rolled back",
                error=str(e),
                job_summary=request.summary,
                exc_info=True,
            )
            raise ValidationError(f"Failed to create job: {str(e)}")

        logger.info(
            "Job created and routed successfully to best matching company",
            job_id=str(created_job.id),
            requesting_company_id=str(request.created_by_company_id),
            identifying_technician_id=str(request.created_by_technician_id),
            selected_company_id=str(best_company_match.company_id),
            matching_score=best_company_match.score,
            required_skills=request.required_skills,
        )

        return CreateJobResult(
            job=created_job,
            routing=persisted_routing,
            matching_score=best_company_match.score,
        )
