"""Create job use case."""

from uuid import UUID
from typing import List
from dataclasses import dataclass

from src.application.interfaces.repositories import (
    JobRepositoryInterface,
    CompanyRepositoryInterface,
    TechnicianRepositoryInterface,
    JobRoutingRepositoryInterface,
)
from src.application.services.job_matching_engine import JobMatchingEngine, JobRequirements
from src.application.services.transactional_outbox import TransactionalOutbox, OutboxEventType
from src.config.logging import get_logger
from src.domain.entities.job import Job
from src.domain.entities.job_routing import JobRouting
from src.domain.exceptions.validation_error import ValidationError
from src.domain.value_objects.address import Address
from src.domain.value_objects.homeowner import Homeowner

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
    routings: List[JobRouting]
    matching_score: float  # Overall matching quality score


class CreateJobUseCase:
    """Use case for creating a job and routing it to available companies."""

    def __init__(
        self,
        job_repo: JobRepositoryInterface,
        company_repo: CompanyRepositoryInterface,
        technician_repo: TechnicianRepositoryInterface,
        job_routing_repo: JobRoutingRepositoryInterface,
        matching_engine: JobMatchingEngine,
        outbox: TransactionalOutbox,
    ):
        self.job_repo = job_repo
        self.company_repo = company_repo
        self.technician_repo = technician_repo
        self.job_routing_repo = job_routing_repo
        self.matching_engine = matching_engine
        self.outbox = outbox

    async def execute(self, request: CreateJobRequest) -> CreateJobResult:
        """Create a new job and route it to available companies using intelligent matching."""
        # IMPORTANTE: Toda a operação deve ser executada em uma única transação
        # Se qualquer parte falhar, nada é salvo (rollback automático)
        
        logger.info(
            "Starting job creation with intelligent matching",
            summary=request.summary,
            category=request.category,
            required_skills=request.required_skills,
            created_by_company_id=str(request.created_by_company_id),
            created_by_technician_id=str(request.created_by_technician_id)
        )
        
        # 1. Validate requesting company exists
        requesting_company = await self.company_repo.get_by_id(request.created_by_company_id)
        if not requesting_company:
            raise ValidationError(f"Requesting company {request.created_by_company_id} not found")

        # 2. Validate identifying technician exists and belongs to requesting company
        identifying_technician = await self.technician_repo.get_by_id(request.created_by_technician_id)
        if not identifying_technician:
            raise ValidationError(f"Identifying technician {request.created_by_technician_id} not found")
        
        if identifying_technician.company_id != request.created_by_company_id:
            raise ValidationError("Identifying technician does not belong to the requesting company")

        # 3. Validate skills and category (if provided)
        if request.required_skills:
            if not isinstance(request.required_skills, list):
                raise ValidationError("Required skills must be a list")
            if not all(isinstance(skill, str) and skill.strip() for skill in request.required_skills):
                raise ValidationError("All required skills must be non-empty strings")
        
        if request.skill_levels:
            if not isinstance(request.skill_levels, dict):
                raise ValidationError("Skill levels must be a dictionary")
            valid_levels = {"basic", "intermediate", "expert"}
            for skill, level in request.skill_levels.items():
                if level not in valid_levels:
                    raise ValidationError(f"Invalid skill level '{level}' for skill '{skill}'. Must be one of: {valid_levels}")

        # 4. Find companies using intelligent matching engine BEFORE creating job
        # This ensures we don't create a job if no companies are available
        job_requirements = JobRequirements(
            job_id=UUID('00000000-0000-0000-0000-000000000000'),  # Temporary ID for matching
            required_skills=request.required_skills or [],
            skill_levels=request.skill_levels or {},
            location={
                "street": request.address.street,
                "city": request.address.city,
                "state": request.address.state,
                "zip_code": request.address.zip_code
            },
            category=request.category
        )
        
        # Get available companies with their skills and provider info
        available_companies = await self.company_repo.find_active_with_skills_and_providers()
        
        if not available_companies:
            raise ValidationError("No active companies with provider configuration found")
        
        # Use matching engine to find best companies
        company_matches = await self.matching_engine.find_matching_companies(
            job_requirements, available_companies, max_results=10
        )
        
        # Filter out the requesting company and ensure we have valid matches
        valid_company_matches = [
            match for match in company_matches 
            if match.company_id != request.created_by_company_id
        ]
        
        if not valid_company_matches:
            raise ValidationError(
                f"No suitable companies found for job requirements. "
                f"Required skills: {request.required_skills or 'None'}, "
                f"Category: {request.category or 'None'}"
            )
        
        logger.info(
            "Found suitable companies for job",
            total_companies=len(available_companies),
            matched_companies=len(valid_company_matches),
            top_matching_score=max(match.score for match in valid_company_matches) if valid_company_matches else 0
        )
        
        # 5. ATOMIC OPERATION: Save job, routings, and outbox events in single transaction
        # NOTA: Como estamos usando AsyncSession, a transação é automática
        # Se qualquer operação falhar, o rollback acontece automaticamente
        
        routings = []
        total_matching_score = 0.0
        
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
                category=request.category
            )
            
            # 5.2. Persist the job
            created_job = await self.job_repo.create(job)
            
            # 5.3. Create and persist routings for matched companies
            for company_match in valid_company_matches:
                routing = JobRouting(
                    job_id=created_job.id,
                    company_id_received=company_match.company_id,
                    sync_status="pending"
                )
                
                # PERSISTIR IMEDIATAMENTE para garantir atomicidade
                persisted_routing = await self.job_routing_repo.create(routing)
                routings.append(persisted_routing)
                
                # 5.4. Create outbox event for immediate sync (atomic operation)
                # Este evento será processado pelo worker para enfileirar Celery task
                await self.outbox.create_event(
                    event_type=OutboxEventType.JOB_SYNC,
                    aggregate_id=str(persisted_routing.id),
                    event_data={
                        "routing_id": str(persisted_routing.id),
                        "job_id": str(created_job.id),
                        "company_id": str(company_match.company_id),
                        "matching_score": company_match.score,
                        "matched_skills": company_match.matched_skills,
                        "provider_type": company_match.provider_type
                    }
                )
                
                total_matching_score += company_match.score
                
                logger.debug(
                    "Created routing and outbox event",
                    routing_id=str(persisted_routing.id),
                    company_id=str(company_match.company_id),
                    matching_score=company_match.score,
                    matched_skills=company_match.matched_skills
                )
            
            # 5.5. Se chegou até aqui, todas as operações foram bem-sucedidas
            # A transação será commitada automaticamente pelo contexto do AsyncSession
            
        except Exception as e:
            # Se qualquer operação falhar, a transação será revertida automaticamente
            logger.error(
                "Failed to create job and routings - transaction will be rolled back",
                error=str(e),
                job_summary=request.summary,
                exc_info=True
            )
            raise ValidationError(f"Failed to create job: {str(e)}")

        # Calculate average matching score
        avg_matching_score = total_matching_score / len(routings) if routings else 0.0

        logger.info(
            "Job created and routed successfully with intelligent matching",
            job_id=str(created_job.id),
            routings_count=len(routings),
            requesting_company_id=str(request.created_by_company_id),
            identifying_technician_id=str(request.created_by_technician_id),
            avg_matching_score=avg_matching_score,
            target_companies=[str(routing.company_id_received) for routing in routings],
            required_skills=request.required_skills,
            category=request.category
        )

        return CreateJobResult(
            job=created_job, 
            routings=routings, 
            matching_score=avg_matching_score
        )
