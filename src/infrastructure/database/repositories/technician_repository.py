"""
Technician repository implementation.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import TechnicianRepositoryInterface
from src.infrastructure.database.models.technician import TechnicianModel


class TechnicianRepository(TechnicianRepositoryInterface):
    """Technician repository implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, technician_id: UUID) -> Optional[TechnicianModel]:
        """Get technician by ID."""
        result = await self.session.execute(
            select(TechnicianModel).where(TechnicianModel.id == technician_id)
        )
        return result.scalar_one_or_none()

    async def get_by_company_id(self, company_id: UUID) -> List[TechnicianModel]:
        """Get all technicians for a company."""
        result = await self.session.execute(
            select(TechnicianModel).where(TechnicianModel.company_id == company_id)
        )
        return result.scalars().all()

    async def create(self, technician: TechnicianModel) -> TechnicianModel:
        """Create a new technician."""
        self.session.add(technician)
        await self.session.flush()
        await self.session.refresh(technician)
        return technician

    async def update(self, technician: TechnicianModel) -> TechnicianModel:
        """Update an existing technician."""
        await self.session.flush()
        await self.session.refresh(technician)
        return technician

    async def delete(self, technician_id: UUID) -> bool:
        """Delete a technician."""
        technician = await self.get_by_id(technician_id)
        if technician:
            await self.session.delete(technician)
            await self.session.flush()
            return True
        return False
