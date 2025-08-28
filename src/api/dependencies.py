"""
FastAPI dependency injection container.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.data_transformer import DataTransformer
from src.application.services.provider_manager import ProviderManager
from src.application.services.job_matching_engine import JobMatchingEngine
from src.application.services.transactional_outbox import TransactionalOutbox
from src.config.database import get_db_session

from src.config.logging import get_logger
from src.infrastructure.database.repositories.company_repository import (
    CompanyRepository,
)
from src.infrastructure.database.repositories.job_repository import JobRepository
from src.infrastructure.database.repositories.job_routing_repository import (
    JobRoutingRepository,
)
from src.infrastructure.database.repositories.technician_repository import (
    TechnicianRepository,
)
from src.infrastructure.providers.factory import ProviderFactory
from src.application.services.rate_limiter import RateLimiter
from src.application.services.retry_handler import RetryHandler

logger = get_logger(__name__)


# Database Dependencies
async def get_company_repository(
    db: AsyncSession = Depends(get_db_session),
) -> CompanyRepository:
    """Get company repository instance."""
    return CompanyRepository(db)


async def get_job_repository(
    db: AsyncSession = Depends(get_db_session),
) -> JobRepository:
    """Get job repository instance."""
    return JobRepository(db)


async def get_job_routing_repository(
    db: AsyncSession = Depends(get_db_session),
) -> JobRoutingRepository:
    """Get job routing repository instance."""
    return JobRoutingRepository(db)


async def get_technician_repository(
    db: AsyncSession = Depends(get_db_session),
) -> TechnicianRepository:
    """Get technician repository instance."""
    return TechnicianRepository(db)


# Service Dependencies
async def get_provider_factory() -> ProviderFactory:
    """Get provider factory instance."""
    return ProviderFactory()


async def get_provider_manager(
    factory: ProviderFactory = Depends(get_provider_factory),
    company_repo: CompanyRepository = Depends(get_company_repository),
) -> ProviderManager:
    """Get provider manager instance."""
    return ProviderManager(factory, company_repo)


async def get_data_transformer() -> DataTransformer:
    """Get data transformer instance."""
    return DataTransformer()


async def get_job_matching_engine() -> JobMatchingEngine:
    """Get job matching engine instance."""
    return JobMatchingEngine()


async def get_transactional_outbox(
    db: AsyncSession = Depends(get_db_session),
) -> TransactionalOutbox:
    """Get transactional outbox instance."""
    return TransactionalOutbox(db)


async def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    return RateLimiter()  # In-memory for now, can be enhanced with Redis


async def get_retry_handler() -> RetryHandler:
    """Get retry handler instance."""
    return RetryHandler()


# Type aliases for cleaner dependency injection
CompanyRepositoryDep = Annotated[CompanyRepository, Depends(get_company_repository)]
JobRepositoryDep = Annotated[JobRepository, Depends(get_job_repository)]
JobRoutingRepositoryDep = Annotated[
    JobRoutingRepository, Depends(get_job_routing_repository)
]
TechnicianRepositoryDep = Annotated[
    TechnicianRepository, Depends(get_technician_repository)
]
ProviderManagerDep = Annotated[ProviderManager, Depends(get_provider_manager)]
DataTransformerDep = Annotated[DataTransformer, Depends(get_data_transformer)]
JobMatchingEngineDep = Annotated[JobMatchingEngine, Depends(get_job_matching_engine)]
TransactionalOutboxDep = Annotated[TransactionalOutbox, Depends(get_transactional_outbox)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
RetryHandlerDep = Annotated[RetryHandler, Depends(get_retry_handler)]
