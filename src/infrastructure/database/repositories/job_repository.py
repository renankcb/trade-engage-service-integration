"""Job repository implementation."""

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import JobRepositoryInterface
from src.config.logging import get_logger
from src.domain.entities.job import Job
from src.infrastructure.database.models.job import JobModel

logger = get_logger(__name__)


class JobRepository(JobRepositoryInterface):
    """Job repository implementation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: UUID) -> Optional[Job]:
        """Get job by ID."""
        stmt = select(JobModel).where(JobModel.id == job_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def create(self, job: Job) -> Job:
        """Create a new job."""
        from src.infrastructure.database.models.job import JobModel

        job_model = JobModel(
            id=job.id,
            summary=job.summary,
            street=job.address.street,
            city=job.address.city,
            state=job.address.state,
            zip_code=job.address.zip_code,
            homeowner_name=job.homeowner_name,
            homeowner_phone=job.homeowner_phone,
            homeowner_email=job.homeowner_email,
            created_by_company_id=job.created_by_company_id,
            created_by_technician_id=job.created_by_technician_id,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

        self.db.add(job_model)
        # Use flush instead of commit to maintain transaction atomicity
        await self.db.flush()
        await self.db.refresh(job_model)

        return self._model_to_entity(job_model)

    async def update(self, job: Job) -> Job:
        """Update an existing job."""
        from src.infrastructure.database.models.job import JobModel

        stmt = select(JobModel).where(JobModel.id == job.id)
        result = await self.db.execute(stmt)
        job_model = result.scalar_one_or_none()

        if not job_model:
            raise ValueError(f"Job {job.id} not found")

        # Update fields
        job_model.summary = job.summary
        job_model.street = job.address.street
        job_model.city = job.address.city
        job_model.state = job.address.state
        job_model.zip_code = job.address.zip_code
        job_model.homeowner_name = job.homeowner_name
        job_model.homeowner_phone = job.homeowner_phone
        job_model.homeowner_email = job.homeowner_email
        job_model.updated_at = job.updated_at

        # Use flush instead of commit to maintain transaction atomicity
        await self.db.flush()
        await self.db.refresh(job_model)

        return self._model_to_entity(job_model)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Job]:
        """Get all jobs with pagination."""
        stmt = select(JobModel).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def get_routings_by_job_id(self, job_id: str) -> List[Any]:
        """Get all routings for a specific job."""
        from src.infrastructure.database.models.job_routing import JobRoutingModel

        # Convert string to UUID
        try:
            job_uuid = UUID(job_id)
        except ValueError:
            logger.warning("Invalid job ID format", job_id=job_id)
            return []

        stmt = select(JobRoutingModel).where(JobRoutingModel.job_id == job_uuid)
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        # Convert to domain entities
        from src.domain.entities.job_routing import JobRouting

        routings = []

        for model in models:
            routing = JobRouting(
                id=model.id,
                job_id=model.job_id,
                company_id_received=model.company_id_received,
                external_id=model.external_id,
                sync_status=model.sync_status,
                retry_count=model.retry_count,
                last_sync_attempt=model.last_sync_attempt,
                last_synced_at=model.last_synced_at,
                next_retry_at=model.next_retry_at,
                error_message=model.error_message,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            routings.append(routing)

        return routings

    def _model_to_entity(self, model: JobModel) -> Job:
        """Convert SQLAlchemy model to domain entity."""
        from src.domain.value_objects.address import Address

        address = Address(
            street=model.street or "",
            city=model.city or "",
            state=model.state or "",
            zip_code=model.zip_code or "",
        )

        return Job(
            id=model.id,
            summary=model.summary,
            address=address,
            homeowner_name=model.homeowner_name or "",
            homeowner_phone=model.homeowner_phone,
            homeowner_email=model.homeowner_email,
            created_by_company_id=model.created_by_company_id,
            created_by_technician_id=model.created_by_technician_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
