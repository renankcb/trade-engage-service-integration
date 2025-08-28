"""
Database configuration and connection management.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from settings."""
    return str(settings.DATABASE_URL)


def create_engine(database_url: str = None):
    """Create async SQLAlchemy engine."""
    url = database_url or get_database_url()

    return create_async_engine(
        url,
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
        future=True,
    )


def get_async_session_factory(
    database_url: str = None,
) -> async_sessionmaker[AsyncSession]:
    """Get async session factory."""
    engine = create_engine(database_url)
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Global session factory
async_session_factory = get_async_session_factory()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
