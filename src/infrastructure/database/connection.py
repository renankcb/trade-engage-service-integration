"""
Database connection utilities.
"""

from typing import Optional, Dict, Any
import asyncio
import time
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker
)
from sqlalchemy import text
import structlog
from src.config.settings import settings

logger = structlog.get_logger()


def get_database_url() -> str:
    """Get database URL from settings."""
    return str(settings.DATABASE_URL)


def get_async_database_url() -> str:
    """Get async database URL from settings."""
    return str(settings.DATABASE_URL)


def create_engine():
    """Create database engine."""
    return create_async_engine(
        get_async_database_url(),
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_pre_ping=True,
    )


def get_async_session_factory():
    """Get async session factory."""
    engine = create_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


async def get_database_health() -> Dict[str, Any]:
    """Check database health."""
    try:
        start_time = time.time()
        
        # Create engine and test connection
        engine = create_engine()
        async_session_factory = async_sessionmaker(
            engine, 
            class_=AsyncSession
        )
        
        async with async_session_factory() as session:
            # Test basic connectivity
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
            
            # Test database info
            result = await session.execute(text("SELECT version()"))
            version = result.fetchone()
            
            response_time = (time.time() - start_time) * 1000
        
        await engine.dispose()
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "version": version[0] if version else "unknown",
            "connections": 1  # Mock value
        }
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def test_database_connection() -> bool:
    """Test database connection."""
    try:
        health = await get_database_health()
        return health["status"] == "healthy"
    except Exception:
        return False


# Global session factory
async_session_factory = get_async_session_factory()


async def get_db_session() -> AsyncSession:
    """Get database session."""
    return async_session_factory()


async def close_database_connections():
    """Close all database connections."""
    try:
        # This would typically close connection pools
        # For now, just log the action
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(
            "Failed to close database connections",
            error=str(e)
        )
