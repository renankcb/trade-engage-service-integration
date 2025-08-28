"""Company repository implementation."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import CompanyRepositoryInterface
from src.config.logging import get_logger
from src.domain.entities.company import Company
from src.infrastructure.database.models.company import CompanyModel
from src.infrastructure.database.models.company_skill import CompanySkillModel
from src.infrastructure.database.models.company_provider_association import CompanyProviderAssociationModel

logger = get_logger(__name__)


class CompanyRepository(CompanyRepositoryInterface):
    """Company repository implementation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        """Get company by ID."""
        stmt = select(CompanyModel).where(CompanyModel.id == company_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def find_active_companies(self) -> List[Company]:
        """Find all active companies."""
        stmt = select(CompanyModel).where(CompanyModel.is_active.is_(True))
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_active_by_provider_type(self) -> List[Company]:
        """Find all active companies that can receive jobs (have provider type)."""
        stmt = select(CompanyModel).where(
            CompanyModel.is_active.is_(True),
            CompanyModel.provider_type.isnot(None)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_active_with_skills_and_providers(self) -> List[dict]:
        """
        Find active companies with their skills and provider information.
        
        Returns:
            List of dictionaries containing company data with skills and provider info
            for intelligent job matching.
        """
        # Complex query to get companies with skills and provider associations
        stmt = select(
            CompanyModel.id,
            CompanyModel.name,
            CompanyModel.is_active,
            CompanyModel.provider_type,
            CompanyModel.provider_config
        ).where(CompanyModel.is_active.is_(True))
        
        result = await self.db.execute(stmt)
        companies_data = []
        
        for row in result.fetchall():
            company_id, name, is_active, provider_type, provider_config = row
            
            # Get company skills
            skills_stmt = select(
                CompanySkillModel.skill_name,
                CompanySkillModel.skill_level,
                CompanySkillModel.is_primary
            ).where(CompanySkillModel.company_id == company_id)
            
            skills_result = await self.db.execute(skills_stmt)
            skills = []
            skill_levels = {}
            primary_skills = {}
            
            for skill_row in skills_result.fetchall():
                skill_name, skill_level, is_primary = skill_row
                skills.append(skill_name)
                skill_levels[skill_name] = skill_level
                primary_skills[skill_name] = is_primary
            
            # Get provider association
            provider_stmt = select(
                CompanyProviderAssociationModel.provider_type,
                CompanyProviderAssociationModel.provider_config,
                CompanyProviderAssociationModel.is_active
            ).where(
                CompanyProviderAssociationModel.company_id == company_id,
                CompanyProviderAssociationModel.is_active.is_(True)
            )
            
            provider_result = await self.db.execute(provider_stmt)
            provider_row = provider_result.fetchone()
            
            if provider_row:
                provider_type, provider_config, provider_active = provider_row
            else:
                provider_type = None
                provider_config = {}
                provider_active = False
            
            company_data = {
                "id": company_id,
                "name": name,
                "is_active": is_active,
                "provider_type": provider_type,
                "provider_config": provider_config,
                "provider_active": provider_active,
                "skills": skills,
                "skill_levels": skill_levels,
                "primary_skills": primary_skills
            }
            
            companies_data.append(company_data)
        
        return companies_data

    def _model_to_entity(self, model: CompanyModel) -> Company:
        """Convert SQLAlchemy model to domain entity."""
        return Company(
            id=model.id,
            name=model.name,
            provider_type=model.provider_type,
            provider_config=model.provider_config or {},
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
