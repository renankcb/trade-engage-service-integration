"""Job-related API endpoints - COMPLETE IMPLEMENTATION."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    CompanyRepositoryDep,
    JobMatchingEngineDep,
    JobRepositoryDep,
    JobRoutingRepositoryDep,
    ProviderManagerDep,
    TechnicianRepositoryDep,
    TransactionalOutboxDep,
    TransactionServiceDep,
)
from src.api.schemas.job import (
    AddressSchema,
    HomeownerSchema,
    JobCreateRequest,
    JobResponse,
    JobRoutingResponse,
)
from src.application.use_cases.create_job import CreateJobRequest, CreateJobUseCase
from src.application.use_cases.sync_job import SyncJobUseCase
from src.config.database import get_db_session
from src.domain.exceptions.sync_error import SyncError
from src.domain.exceptions.validation_error import ValidationError
from src.domain.value_objects.homeowner import Homeowner
from src.domain.value_objects.sync_status import SyncStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreateRequest,
    job_repository: JobRepositoryDep,
    company_repository: CompanyRepositoryDep,
    technician_repository: TechnicianRepositoryDep,
    job_routing_repository: JobRoutingRepositoryDep,
    matching_engine: JobMatchingEngineDep,
    outbox: TransactionalOutboxDep,
    transaction_service: TransactionServiceDep,
):
    """Create a new job and route it to available companies."""
    try:
        use_case = CreateJobUseCase(
            job_repo=job_repository,
            company_repo=company_repository,
            technician_repo=technician_repository,
            job_routing_repo=job_routing_repository,
            matching_engine=matching_engine,
            outbox=outbox,
            transaction_service=transaction_service,
        )

        request = CreateJobRequest(
            summary=job_data.summary,
            address=job_data.address,
            homeowner=job_data.homeowner,
            created_by_company_id=job_data.created_by_company_id,
            created_by_technician_id=job_data.created_by_technician_id,
            required_skills=job_data.required_skills,
            skill_levels=job_data.skill_levels,
        )

        result = await use_case.execute(request)

        logger.info(
            "Job created and routed successfully",
            job_id=str(result.job.id),
            routing_id=str(result.routing.id),
            requesting_company_id=str(result.job.created_by_company_id),
            identifying_technician_id=str(result.job.created_by_technician_id),
        )

        return JobResponse(
            id=str(result.job.id),
            summary=result.job.summary,
            address=AddressSchema(
                street=result.job.address.street,
                city=result.job.address.city,
                state=result.job.address.state,
                zip_code=result.job.address.zip_code,
            ),
            homeowner=HomeownerSchema(
                name=result.job.homeowner_name,
                phone=result.job.homeowner_phone,
                email=result.job.homeowner_email,
            ),
            created_by_company_id=str(result.job.created_by_company_id),
            created_by_technician_id=str(result.job.created_by_technician_id),
            status=result.job.status,
            completed_at=result.job.completed_at,
            created_at=result.job.created_at,
            updated_at=result.job.updated_at,
            selected_company_id=str(result.routing.company_id_received),
            matching_score=result.matching_score,
        )

    except ValidationError as e:
        logger.warning("Validation error creating job", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to create job", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job",
        )


@router.post("/{job_id}/sync", response_model=JobRoutingResponse)
async def sync_job(
    job_id: str,
    company_id: str,
    job_repository: JobRepositoryDep,
    company_repository: CompanyRepositoryDep,
    provider_manager: ProviderManagerDep,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Sync a specific job to a specific company."""
    try:
        use_case = SyncJobUseCase(
            job_repository=job_repository,
            company_repository=company_repository,
            provider_manager=provider_manager,
        )

        result = await use_case.execute(
            job_id=job_id,
            company_id=company_id,
        )

        logger.info(
            "Job synced successfully",
            job_id=job_id,
            company_id=company_id,
            external_id=result.external_id,
        )

        return JobRoutingResponse(
            id=result.id,
            job_id=result.job_id,
            company_id_received=result.company_id_received,
            sync_status=result.sync_status.value,
            external_id=result.external_id,
            retry_count=result.retry_count,
            last_synced_at=result.last_synced_at,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    except SyncError as e:
        logger.warning(
            "Job sync failed",
            job_id=job_id,
            company_id=company_id,
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error during job sync",
            job_id=job_id,
            company_id=company_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/{job_id}/routings", response_model=list[JobRoutingResponse])
async def get_job_routings(
    job_id: str,
    job_repository: JobRepositoryDep,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get all routings for a specific job."""
    try:
        routings = await job_repository.get_routings_by_job_id(job_id)

        return [
            JobRoutingResponse(
                id=str(routing.id),
                job_id=str(routing.job_id),
                company_id_received=str(routing.company_id_received),
                sync_status=routing.sync_status,
                external_id=routing.external_id,
                retry_count=routing.retry_count,
                last_synced_at=routing.last_synced_at,
                error_message=routing.error_message,
                created_at=routing.created_at,
                updated_at=routing.updated_at,
            )
            for routing in routings
        ]

    except Exception as e:
        logger.error(
            "Failed to get job routings",
            job_id=job_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job routings",
        )


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    job_repository: JobRepositoryDep,
    db_session: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100,
):
    """List all jobs with pagination."""
    try:
        jobs = await job_repository.get_all(skip=skip, limit=limit)

        return [
            JobResponse(
                id=job.id,
                summary=job.summary,
                address=job.address,
                homeowner=Homeowner(
                    name=job.homeowner_name,
                    phone=job.homeowner_phone,
                    email=job.homeowner_email,
                ),
                created_by_company_id=job.created_by_company_id,
                created_by_technician_id=job.created_by_technician_id,
                created_at=job.created_at,
                updated_at=job.updated_at,
                routings=[],  # Don't include routings in list view
            )
            for job in jobs
        ]

    except Exception as e:
        logger.error("Failed to list jobs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs",
        )
