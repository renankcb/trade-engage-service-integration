"""
Job routing repository implementation.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.interfaces.repositories import JobRoutingRepositoryInterface
from src.config.logging import get_logger
from src.domain.entities.job_routing import JobRouting
from src.domain.value_objects.sync_status import SyncStatus
from src.infrastructure.database.models.job_routing import JobRoutingModel

logger = get_logger(__name__)


class JobRoutingRepository(JobRoutingRepositoryInterface):
    """Job routing repository implementation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, job_routing: JobRouting) -> JobRouting:
        """Create a new job routing."""
        model = JobRoutingModel(
            id=job_routing.id,
            job_id=job_routing.job_id,
            company_id_received=job_routing.company_id_received,
            external_id=job_routing.external_id,
            sync_status=job_routing.sync_status.value
            if hasattr(job_routing.sync_status, "value")
            else job_routing.sync_status,
            retry_count=job_routing.retry_count,
            last_synced_at=job_routing.last_synced_at,
            error_message=job_routing.error_message,
        )

        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)

        logger.info("Job routing created", job_routing_id=str(model.id))
        return self._model_to_entity(model)

    async def get_by_id(self, job_routing_id: UUID) -> Optional[JobRouting]:
        """Get job routing by ID."""
        stmt = select(JobRoutingModel).where(JobRoutingModel.id == job_routing_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_job_id(self, job_id: UUID) -> List[JobRouting]:
        """Get all job routings for a specific job."""
        stmt = select(JobRoutingModel).where(JobRoutingModel.job_id == job_id)
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_by_status(
        self, status: SyncStatus, limit: int = 100
    ) -> List[JobRouting]:
        """Find job routings by sync status."""
        stmt = (
            select(JobRoutingModel)
            .where(JobRoutingModel.sync_status == status)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_pending_sync(self, limit: int = 50) -> List[JobRouting]:
        """Find job routings ready for sync."""
        stmt = (
            select(JobRoutingModel)
            .where(
                and_(
                    JobRoutingModel.sync_status.in_(
                        [SyncStatus.PENDING.value, SyncStatus.FAILED.value]
                    ),
                    JobRoutingModel.retry_count < 3,  # Max retries
                )
            )
            .options(selectinload(JobRoutingModel.job))
            .options(selectinload(JobRoutingModel.company_received))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_stuck_pending_routings(
        self, limit: int = 20, older_than_minutes: int = 5
    ) -> List[JobRouting]:
        """
        Find job routings that are stuck in pending/failed status.

        This method is used by the backup task to find routings that:
        1. Have been in pending/failed status for too long
        2. May have been missed by the OutboxWorker
        3. Need backup processing

        Args:
            limit: Maximum number of routings to return
            older_than_minutes: Only return routings older than this many minutes

        Returns:
            List of stuck job routings
        """
        # Calculate the cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)

        stmt = (
            select(JobRoutingModel)
            .where(
                and_(
                    JobRoutingModel.sync_status.in_(
                        [SyncStatus.PENDING.value, SyncStatus.FAILED.value]
                    ),
                    JobRoutingModel.retry_count < 3,  # Max retries
                    JobRoutingModel.updated_at < cutoff_time,  # Older than cutoff
                    # Exclude routings that are currently being processed
                    JobRoutingModel.sync_status != SyncStatus.PROCESSING.value,
                )
            )
            .options(selectinload(JobRoutingModel.job))
            .options(selectinload(JobRoutingModel.company_received))
            .order_by(JobRoutingModel.updated_at.asc())  # Process oldest first
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        models = result.scalars().all()

        stuck_routings = [self._model_to_entity(model) for model in models]

        logger.info(
            "Found stuck pending routings",
            count=len(stuck_routings),
            older_than_minutes=older_than_minutes,
            limit=limit,
        )

        return stuck_routings

    async def claim_pending_routings(self, limit: int = 50) -> List[JobRouting]:
        """Claim pending routings atomically to prevent duplicates.

        This method implements a claim pattern where pending routings are
        marked as 'processing' atomically, preventing multiple workers
        from processing the same routing.
        """
        stmt = (
            select(JobRoutingModel)
            .where(
                and_(
                    JobRoutingModel.sync_status.in_(
                        [SyncStatus.PENDING.value, SyncStatus.FAILED.value]
                    ),
                    JobRoutingModel.retry_count < 3,  # Max retries
                    or_(
                        JobRoutingModel.next_retry_at.is_(None),
                        JobRoutingModel.next_retry_at <= datetime.now(timezone.utc),
                    ),
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        pending_models = result.scalars().all()

        if not pending_models:
            return []

        # Claim these routings atomically by updating their status
        routing_ids = [model.id for model in pending_models]
        claim_stmt = (
            update(JobRoutingModel)
            .where(
                and_(
                    JobRoutingModel.id.in_(routing_ids),
                    JobRoutingModel.sync_status.in_(
                        [SyncStatus.PENDING.value, SyncStatus.FAILED.value]
                    ),
                    JobRoutingModel.retry_count < 3,
                )
            )
            .values(
                sync_status=SyncStatus.PROCESSING.value,
                claimed_at=datetime.now(timezone.utc),
            )
            .returning(JobRoutingModel.id)
        )

        claimed_result = await self.db.execute(claim_stmt)
        claimed_ids = [row[0] for row in claimed_result.fetchall()]

        # Fetch the claimed routings with full data
        if claimed_ids:
            claimed_stmt = (
                select(JobRoutingModel)
                .where(JobRoutingModel.id.in_(claimed_ids))
                .options(selectinload(JobRoutingModel.job))
                .options(selectinload(JobRoutingModel.company_received))
            )
            claimed_result = await self.db.execute(claimed_stmt)
            claimed_models = claimed_result.scalars().all()

            logger.info(
                "Successfully claimed pending routings",
                claimed_count=len(claimed_models),
                routing_ids=[str(model.id) for model in claimed_models],
            )

            return [self._model_to_entity(model) for model in claimed_models]

        return []

    async def mark_sync_failed(
        self, routing_id: UUID, error_message: str
    ) -> JobRouting:
        """Mark a job routing as failed with error message."""
        stmt = (
            update(JobRoutingModel)
            .where(JobRoutingModel.id == routing_id)
            .values(
                sync_status=SyncStatus.FAILED.value,
                error_message=error_message,
                retry_count=JobRoutingModel.retry_count + 1,
                next_retry_at=datetime.now(timezone.utc)
                + timedelta(minutes=5 * (2**JobRoutingModel.retry_count)),
            )
            .returning(JobRoutingModel)
        )

        result = await self.db.execute(stmt)
        updated_model = result.scalar_one()

        logger.info(
            "Job routing marked as failed",
            routing_id=str(routing_id),
            error_message=error_message,
            retry_count=updated_model.retry_count,
        )

    async def find_synced_for_polling(self, limit: int = 100) -> List[JobRouting]:
        """Find synced job routings that need status polling."""
        stmt = (
            select(JobRoutingModel)
            .where(JobRoutingModel.sync_status == SyncStatus.SYNCED.value)
            .options(selectinload(JobRoutingModel.company_received))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_failed_for_retry(self, limit: int = 25) -> List[JobRouting]:
        """Find failed job routings that should be retried."""
        stmt = (
            select(JobRoutingModel)
            .where(
                and_(
                    JobRoutingModel.sync_status == SyncStatus.FAILED.value,
                    JobRoutingModel.retry_count < 3,
                    or_(
                        JobRoutingModel.next_retry_at.is_(None),
                        JobRoutingModel.next_retry_at <= datetime.now(timezone.utc),
                    ),
                )
            )
            .options(selectinload(JobRoutingModel.job))
            .options(selectinload(JobRoutingModel.company_received))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def update(self, job_routing: JobRouting) -> JobRouting:
        """Update job routing."""
        stmt = (
            update(JobRoutingModel)
            .where(JobRoutingModel.id == job_routing.id)
            .values(
                external_id=job_routing.external_id,
                sync_status=job_routing.sync_status.value
                if hasattr(job_routing.sync_status, "value")
                else job_routing.sync_status,
                retry_count=job_routing.retry_count,
                last_synced_at=job_routing.last_synced_at,
                next_retry_at=job_routing.next_retry_at,
                error_message=job_routing.error_message,
                updated_at=datetime.now(timezone.utc),
            )
        )

        await self.db.execute(stmt)
        await self.db.flush()

        # Fetch updated record
        updated = await self.get_by_id(job_routing.id)
        logger.info("Job routing updated", job_routing_id=str(job_routing.id))
        return updated

    async def delete(self, job_routing_id: UUID) -> bool:
        """Delete job routing."""
        stmt = select(JobRoutingModel).where(JobRoutingModel.id == job_routing_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.db.delete(model)
            await self.db.flush()
            logger.info("Job routing deleted", job_routing_id=str(job_routing_id))
            return True

        return False

    def _model_to_entity(self, model: JobRoutingModel) -> JobRouting:
        """Convert SQLAlchemy model to domain entity."""
        return JobRouting(
            id=model.id,
            job_id=model.job_id,
            company_id_received=model.company_id_received,
            external_id=model.external_id,
            sync_status=model.sync_status,
            retry_count=model.retry_count,
            last_synced_at=model.last_synced_at,
            next_retry_at=model.next_retry_at,
            error_message=model.error_message,
            claimed_at=model.claimed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
