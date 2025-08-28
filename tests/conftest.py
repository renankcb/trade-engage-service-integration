"""
Pytest configuration and fixtures.
"""

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.application.interfaces.providers import ProviderInterface
from src.application.interfaces.repositories import (
    CompanyRepositoryInterface,
    JobRepositoryInterface,
    JobRoutingRepositoryInterface,
)
from src.application.services.provider_manager import ProviderManager
from src.config.settings import Settings
from src.infrastructure.database.models import Base

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Test settings configuration."""
    return Settings(
        ENVIRONMENT="test",
        DATABASE_URL=TEST_DATABASE_URL,
        REDIS_URL="redis://localhost:6379/1",
        SECRET_KEY="test-secret-key",
        SERVICETITAN_CLIENT_ID="test_client_id",
        SERVICETITAN_CLIENT_SECRET="test_client_secret",
        SERVICETITAN_TENANT_ID="test_tenant_id",
        DEBUG=True,
        LOG_LEVEL="DEBUG",
        MOCK_PROVIDERS=True,
        ENABLE_DEBUG_ROUTES=True,
    )


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_job_routing_repository():
    """Mock job routing repository."""
    mock_repo = AsyncMock(spec=JobRoutingRepositoryInterface)

    # Mock methods
    mock_repo.get_by_id = AsyncMock()
    mock_repo.find_pending_sync = AsyncMock(return_value=[])
    mock_repo.find_synced_for_polling = AsyncMock(return_value=[])
    mock_repo.find_failed_for_retry = AsyncMock(return_value=[])
    mock_repo.update = AsyncMock()
    mock_repo.delete_old_completed_routings = AsyncMock(return_value=0)

    return mock_repo


@pytest.fixture
def mock_job_repository():
    """Mock job repository."""
    mock_repo = AsyncMock(spec=JobRepositoryInterface)

    # Mock methods
    mock_repo.get_by_id = AsyncMock()
    mock_repo.update = AsyncMock()

    return mock_repo


@pytest.fixture
def mock_company_repository():
    """Mock company repository."""
    mock_repo = AsyncMock(spec=CompanyRepositoryInterface)

    # Mock methods
    mock_repo.get_by_id = AsyncMock()

    return mock_repo


@pytest.fixture
def mock_provider():
    """Mock provider implementation."""
    mock_provider = AsyncMock(spec=ProviderInterface)

    # Mock methods
    mock_provider.name = "MockProvider"
    mock_provider.create_lead = AsyncMock()
    mock_provider.get_job_status = AsyncMock()
    mock_provider.batch_get_job_status = AsyncMock(return_value=[])
    mock_provider.validate_config = AsyncMock(return_value=True)

    return mock_provider


@pytest.fixture
def mock_provider_manager(mock_provider):
    """Mock provider manager."""
    mock_manager = MagicMock(spec=ProviderManager)
    mock_manager.get_provider = MagicMock(return_value=mock_provider)

    return mock_manager


@pytest.fixture
def client(test_settings):
    """Create test FastAPI client."""
    from fastapi.testclient import TestClient

    from src.api.app import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "summary": "Test job summary",
        "street": "123 Test St",
        "city": "Test City",
        "state": "TX",
        "zip_code": "12345",
        "homeowner_name": "John Doe",
        "homeowner_phone": "555-1234",
        "homeowner_email": "john@example.com",
        "created_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
        "created_by_technician_id": "550e8400-e29b-41d4-a716-446655440001",
    }


@pytest.fixture
def sample_job_routing_data():
    """Sample job routing data for testing."""
    return {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "company_id_received": "550e8400-e29b-41d4-a716-446655440002",
        "external_id": "ext_123",
        "sync_status": "pending",
    }
