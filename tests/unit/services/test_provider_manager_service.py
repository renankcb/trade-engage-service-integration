"""
Unit tests for ProviderManager.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.interfaces.providers import (
    CreateLeadRequest,
    CreateLeadResponse,
    ProviderHealthStatus,
    ProviderInterface,
)
from src.application.services.provider_manager import ProviderManager
from src.domain.entities.company import Company
from src.domain.entities.job import Job
from src.domain.exceptions.provider_error import (
    ProviderAPIError,
    ProviderConfigurationError,
)
from src.domain.value_objects.address import Address
from src.domain.value_objects.homeowner import Homeowner
from src.domain.value_objects.provider_type import ProviderType


class MockProvider(ProviderInterface):
    """Mock provider for testing."""

    def __init__(
        self,
        name: str = "Mock Provider",
        provider_type: ProviderType = ProviderType.MOCK,
    ):
        self._name = name
        self._provider_type = provider_type
        self._is_healthy = True
        self._response_time = 100

    @property
    def name(self) -> str:
        return self._name

    @property
    def provider_type(self) -> ProviderType:
        return self._provider_type

    async def create_lead(self, request: CreateLeadRequest) -> CreateLeadResponse:
        return CreateLeadResponse(success=True, external_id=f"mock_{uuid4().hex[:8]}")

    async def get_job_status(self, external_id: str, config: dict) -> dict:
        return {"external_id": external_id, "status": "pending", "is_completed": False}

    async def batch_get_job_status(self, external_ids: list, config: dict) -> list:
        return [
            {"external_id": ext_id, "status": "pending", "is_completed": False}
            for ext_id in external_ids
        ]

    def validate_config(self, config: dict) -> bool:
        return True

    async def validate_config_async(self) -> bool:
        return True

    async def get_health_status(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(
            is_healthy=self._is_healthy,
            status_message="Healthy" if self._is_healthy else "Unhealthy",
            last_check="2024-01-01T00:00:00Z",
            response_time_ms=self._response_time,
        )

    def set_health_status(self, is_healthy: bool, response_time: int = 100):
        self._is_healthy = is_healthy
        self._response_time = response_time


class TestProviderManager:
    """Test cases for ProviderManager."""

    @pytest.fixture
    def mock_provider_factory(self):
        """Create a mock provider factory."""
        factory = MagicMock()
        factory.get_provider = MagicMock()
        factory.create_provider = MagicMock()
        return factory

    @pytest.fixture
    def mock_company_repository(self):
        """Create a mock company repository."""
        repository = AsyncMock()
        repository.get_by_id = AsyncMock()
        repository.find_by_provider_type = AsyncMock()
        repository.find_active = AsyncMock()
        return repository

    @pytest.fixture
    def mock_rate_limiter(self):
        """Create a mock rate limiter."""
        rate_limiter = AsyncMock()
        rate_limiter.check_rate_limit = AsyncMock()
        return rate_limiter

    @pytest.fixture
    def mock_retry_handler(self):
        """Create a mock retry handler."""
        retry_handler = AsyncMock()
        retry_handler.execute_with_retry = AsyncMock()
        return retry_handler

    @pytest.fixture
    def sample_company(self):
        """Create a sample company for testing."""
        return Company(
            name="Test Company",
            provider_type=ProviderType.SERVICETITAN,
            provider_config={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "tenant_id": "test_tenant_id",
            },
        )

    @pytest.fixture
    def sample_job(self):
        """Create a sample job for testing."""
        address = Address(
            street="123 Test St", city="Test City", state="TX", zip_code="12345"
        )
        return Job(
            summary="Test job summary",
            address=address,
            homeowner_name="John Doe",
            homeowner_phone="555-1234",
            homeowner_email="john@example.com",
            created_by_company_id=uuid4(),
            created_by_technician_id=uuid4(),
            required_skills=["plumbing"],
            skill_levels={"plumbing": "expert"},
        )

    @pytest.fixture
    def sample_lead_request(self, sample_job):
        """Create a sample lead request for testing."""
        return CreateLeadRequest(
            job=sample_job,
            company_config={"test": "config"},
            idempotency_key="test_key_123",
        )

    @pytest.fixture
    def sample_lead_response(self):
        """Create a sample lead response for testing."""
        return CreateLeadResponse(success=True, external_id="ext_123")

    @pytest.fixture
    def provider_manager(
        self,
        mock_provider_factory,
        mock_company_repository,
        mock_rate_limiter,
        mock_retry_handler,
    ):
        """Create a ProviderManager instance for testing."""
        return ProviderManager(
            provider_factory=mock_provider_factory,
            company_repository=mock_company_repository,
            rate_limiter=mock_rate_limiter,
            retry_handler=mock_retry_handler,
        )

    @pytest.fixture
    def provider_manager_no_optional(
        self, mock_provider_factory, mock_company_repository
    ):
        """Create a ProviderManager instance without optional dependencies."""
        return ProviderManager(
            provider_factory=mock_provider_factory,
            company_repository=mock_company_repository,
        )

    @pytest.mark.asyncio
    async def test_get_provider_for_company_success(
        self,
        provider_manager,
        mock_company_repository,
        mock_provider_factory,
        sample_company,
    ):
        """Test successful provider retrieval for a company."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider

        # Act
        result = await provider_manager.get_provider_for_company(company_id)

        # Assert
        assert result is not None
        assert result == mock_provider
        mock_company_repository.get_by_id.assert_called_once_with(company_id)
        mock_provider_factory.get_provider.assert_called_once_with(
            sample_company.provider_type
        )

    @pytest.mark.asyncio
    async def test_get_provider_for_company_not_found(
        self, provider_manager, mock_company_repository
    ):
        """Test provider retrieval when company is not found."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = None

        # Act
        result = await provider_manager.get_provider_for_company(company_id)

        # Assert
        assert result is None
        mock_company_repository.get_by_id.assert_called_once_with(company_id)

    @pytest.mark.asyncio
    async def test_get_provider_for_company_provider_not_found(
        self,
        provider_manager,
        mock_company_repository,
        mock_provider_factory,
        sample_company,
    ):
        """Test provider retrieval when provider is not found."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company
        mock_provider_factory.get_provider.return_value = None

        # Act
        result = await provider_manager.get_provider_for_company(company_id)

        # Assert
        assert result is None
        mock_company_repository.get_by_id.assert_called_once_with(company_id)
        mock_provider_factory.get_provider.assert_called_once_with(
            sample_company.provider_type
        )

    @pytest.mark.asyncio
    async def test_get_provider_for_company_repository_error(
        self, provider_manager, mock_company_repository
    ):
        """Test provider retrieval when repository raises an exception."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.side_effect = Exception("Database error")

        # Act
        result = await provider_manager.get_provider_for_company(company_id)

        # Assert
        assert result is None
        mock_company_repository.get_by_id.assert_called_once_with(company_id)

    def test_get_provider_success(self, provider_manager, mock_provider_factory):
        """Test successful provider retrieval by type."""
        # Arrange
        provider_type = ProviderType.SERVICETITAN
        mock_provider = MockProvider()
        mock_provider_factory.create_provider.return_value = mock_provider

        # Act
        result = provider_manager.get_provider(provider_type)

        # Assert
        assert result == mock_provider
        mock_provider_factory.create_provider.assert_called_once_with(provider_type)

    def test_get_provider_not_found(self, provider_manager, mock_provider_factory):
        """Test provider retrieval when provider type is not found."""
        # Arrange
        provider_type = ProviderType.SERVICETITAN
        mock_provider_factory.create_provider.return_value = None

        # Act & Assert
        with pytest.raises(ProviderConfigurationError) as exc_info:
            provider_manager.get_provider(provider_type)

        assert f"Provider {provider_type.value} not found" in str(exc_info.value)
        mock_provider_factory.create_provider.assert_called_once_with(provider_type)

    @pytest.mark.asyncio
    async def test_create_lead_success_with_retry_handler(
        self,
        provider_manager,
        mock_company_repository,
        mock_provider_factory,
        mock_rate_limiter,
        mock_retry_handler,
        sample_company,
        sample_lead_request,
        sample_lead_response,
    ):
        """Test successful lead creation with retry handler."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider
        mock_retry_handler.execute_with_retry.return_value = sample_lead_response

        # Act
        result = await provider_manager.create_lead(company_id, sample_lead_request)

        # Assert
        assert result == sample_lead_response
        mock_company_repository.get_by_id.assert_called_once_with(company_id)
        mock_provider_factory.get_provider.assert_called_once_with(
            sample_company.provider_type
        )
        mock_rate_limiter.check_rate_limit.assert_called_once_with(
            f"create_lead:{company_id}"
        )
        mock_retry_handler.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_lead_success_without_retry_handler(
        self,
        provider_manager_no_optional,
        mock_company_repository,
        mock_provider_factory,
        sample_company,
        sample_lead_request,
        sample_lead_response,
    ):
        """Test successful lead creation without retry handler."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider

        # Mock the provider's create_lead method
        mock_provider.create_lead = AsyncMock(return_value=sample_lead_response)

        # Act
        result = await provider_manager_no_optional.create_lead(
            company_id, sample_lead_request
        )

        # Assert
        assert result == sample_lead_response
        mock_company_repository.get_by_id.assert_called_once_with(company_id)
        mock_provider_factory.get_provider.assert_called_once_with(
            sample_company.provider_type
        )

    @pytest.mark.asyncio
    async def test_create_lead_rate_limit_exceeded(
        self,
        provider_manager,
        mock_company_repository,
        mock_provider_factory,
        mock_rate_limiter,
        sample_company,
        sample_lead_request,
    ):
        """Test lead creation when rate limit is exceeded."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider

        # Mock rate limiter to raise an exception
        mock_rate_limiter.check_rate_limit.side_effect = Exception(
            "Rate limit exceeded"
        )

        # Act & Assert
        with pytest.raises(ProviderAPIError) as exc_info:
            await provider_manager.create_lead(company_id, sample_lead_request)

        # The ProviderManager should catch the exception and re-raise as ProviderAPIError
        # with the correct signature (provider, status_code, message)
        assert exc_info.value.provider == "unknown"
        assert exc_info.value.status_code == 0
        assert "Failed to create lead: Rate limit exceeded" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_lead_provider_api_error(
        self,
        provider_manager,
        mock_company_repository,
        mock_provider_factory,
        mock_rate_limiter,
        mock_retry_handler,
        sample_company,
        sample_lead_request,
    ):
        """Test lead creation when provider API returns an error."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider

        # Mock retry handler to raise ProviderAPIError
        provider_error = ProviderAPIError("servicetitan", 400, "Bad request")
        mock_retry_handler.execute_with_retry.side_effect = provider_error

        # Act & Assert
        with pytest.raises(ProviderAPIError) as exc_info:
            await provider_manager.create_lead(company_id, sample_lead_request)

        assert exc_info.value == provider_error

    @pytest.mark.asyncio
    async def test_create_lead_unexpected_error(
        self,
        provider_manager,
        mock_company_repository,
        mock_provider_factory,
        mock_rate_limiter,
        mock_retry_handler,
        sample_company,
        sample_lead_request,
    ):
        """Test lead creation when an unexpected error occurs."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider

        # Mock retry handler to raise an unexpected error
        mock_retry_handler.execute_with_retry.side_effect = Exception(
            "Unexpected error"
        )

        # Act & Assert
        with pytest.raises(ProviderAPIError) as exc_info:
            await provider_manager.create_lead(company_id, sample_lead_request)

        # The ProviderManager should catch the exception and re-raise as ProviderAPIError
        # with the correct signature (provider, status_code, message)
        assert exc_info.value.provider == "unknown"
        assert exc_info.value.status_code == 0
        assert "Failed to create lead: Unexpected error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_active_companies_all(
        self, provider_manager, mock_company_repository
    ):
        """Test getting all active companies."""
        # Arrange
        companies = [
            Company(
                name="Company A",
                provider_type=ProviderType.SERVICETITAN,
                provider_config={},
            ),
            Company(
                name="Company B",
                provider_type=ProviderType.HOUSECALLPRO,
                provider_config={},
            ),
            Company(
                name="Company C", provider_type=ProviderType.MOCK, provider_config={}
            ),
        ]
        mock_company_repository.find_active.return_value = companies

        # Act
        result = await provider_manager.get_active_companies()

        # Assert
        assert len(result) == 3
        assert all(company.is_active for company in result)
        mock_company_repository.find_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_companies_by_provider_type(
        self, provider_manager, mock_company_repository
    ):
        """Test getting active companies filtered by provider type."""
        # Arrange
        provider_type = ProviderType.SERVICETITAN
        companies = [
            Company(
                name="Company A",
                provider_type=ProviderType.SERVICETITAN,
                provider_config={},
            ),
            Company(
                name="Company B",
                provider_type=ProviderType.SERVICETITAN,
                provider_config={},
            ),
        ]
        mock_company_repository.find_by_provider_type.return_value = companies

        # Act
        result = await provider_manager.get_active_companies(provider_type)

        # Assert
        assert len(result) == 2
        assert all(company.provider_type == provider_type for company in result)
        mock_company_repository.find_by_provider_type.assert_called_once_with(
            provider_type
        )

    @pytest.mark.asyncio
    async def test_get_active_companies_repository_error(
        self, provider_manager, mock_company_repository
    ):
        """Test getting active companies when repository raises an exception."""
        # Arrange
        mock_company_repository.find_active.side_effect = Exception("Database error")

        # Act
        result = await provider_manager.get_active_companies()

        # Assert
        assert result == []
        mock_company_repository.find_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_companies_by_provider_type_repository_error(
        self, provider_manager, mock_company_repository
    ):
        """Test getting active companies by provider type when repository raises an exception."""
        # Arrange
        provider_type = ProviderType.SERVICETITAN
        mock_company_repository.find_by_provider_type.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await provider_manager.get_active_companies(provider_type)

        # Assert
        assert result == []
        mock_company_repository.find_by_provider_type.assert_called_once_with(
            provider_type
        )

    @pytest.mark.asyncio
    async def test_validate_provider_config_no_provider(
        self, provider_manager, mock_company_repository
    ):
        """Test provider configuration validation when no provider is found."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = None

        # Act
        result = await provider_manager.validate_provider_config(company_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_provider_config_provider_error(
        self,
        provider_manager,
        mock_company_repository,
        mock_provider_factory,
        sample_company,
    ):
        """Test provider configuration validation when provider raises an exception."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider

        # Mock provider to raise an exception during validation
        mock_provider.validate_config_async = AsyncMock(
            side_effect=Exception("Validation error")
        )

        # Act
        result = await provider_manager.validate_provider_config(company_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_provider_status_no_provider(
        self, provider_manager, mock_company_repository
    ):
        """Test provider status retrieval when no provider is found."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = None

        # Act
        result = await provider_manager.get_provider_status(company_id)

        # Assert
        assert result["status"] == "no_provider"
        assert "Provider not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_provider_status_provider_error(
        self,
        provider_manager,
        mock_company_repository,
        mock_provider_factory,
        sample_company,
    ):
        """Test provider status retrieval when provider raises an exception."""
        # Arrange
        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider

        # Mock provider to raise an exception during health check
        mock_provider.get_health_status = AsyncMock(
            side_effect=Exception("Health check error")
        )

        # Act
        result = await provider_manager.get_provider_status(company_id)

        # Assert
        assert result["status"] == "error"
        assert "Health check error" in result["error"]

    def test_provider_manager_initialization_with_all_dependencies(
        self,
        mock_provider_factory,
        mock_company_repository,
        mock_rate_limiter,
        mock_retry_handler,
    ):
        """Test ProviderManager initialization with all dependencies."""
        # Act
        manager = ProviderManager(
            provider_factory=mock_provider_factory,
            company_repository=mock_company_repository,
            rate_limiter=mock_rate_limiter,
            retry_handler=mock_retry_handler,
        )

        # Assert
        assert manager.provider_factory == mock_provider_factory
        assert manager.company_repository == mock_company_repository
        assert manager.rate_limiter == mock_rate_limiter
        assert manager.retry_handler == mock_retry_handler

    def test_provider_manager_initialization_without_optional_dependencies(
        self, mock_provider_factory, mock_company_repository
    ):
        """Test ProviderManager initialization without optional dependencies."""
        # Act
        manager = ProviderManager(
            provider_factory=mock_provider_factory,
            company_repository=mock_company_repository,
        )

        # Assert
        assert manager.provider_factory == mock_provider_factory
        assert manager.company_repository == mock_company_repository
        assert manager.rate_limiter is None
        assert manager.retry_handler is None

    @pytest.mark.asyncio
    async def test_create_lead_with_rate_limiter_only(
        self,
        mock_provider_factory,
        mock_company_repository,
        mock_rate_limiter,
        sample_company,
        sample_lead_request,
        sample_lead_response,
    ):
        """Test lead creation with only rate limiter (no retry handler)."""
        # Arrange
        manager = ProviderManager(
            provider_factory=mock_provider_factory,
            company_repository=mock_company_repository,
            rate_limiter=mock_rate_limiter,
        )

        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider
        mock_provider.create_lead = AsyncMock(return_value=sample_lead_response)

        # Act
        result = await manager.create_lead(company_id, sample_lead_request)

        # Assert
        assert result == sample_lead_response
        mock_rate_limiter.check_rate_limit.assert_called_once_with(
            f"create_lead:{company_id}"
        )

    @pytest.mark.asyncio
    async def test_create_lead_with_retry_handler_only(
        self,
        mock_provider_factory,
        mock_company_repository,
        mock_retry_handler,
        sample_company,
        sample_lead_request,
        sample_lead_response,
    ):
        """Test lead creation with only retry handler (no rate limiter)."""
        # Arrange
        manager = ProviderManager(
            provider_factory=mock_provider_factory,
            company_repository=mock_company_repository,
            retry_handler=mock_retry_handler,
        )

        company_id = uuid4()
        mock_company_repository.get_by_id.return_value = sample_company

        mock_provider = MockProvider()
        mock_provider_factory.get_provider.return_value = mock_provider
        mock_retry_handler.execute_with_retry.return_value = sample_lead_response

        # Act
        result = await manager.create_lead(company_id, sample_lead_request)

        # Assert
        assert result == sample_lead_response
        mock_retry_handler.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_companies_empty_result(
        self, provider_manager, mock_company_repository
    ):
        """Test getting active companies when repository returns empty list."""
        # Arrange
        mock_company_repository.find_active.return_value = []

        # Act
        result = await provider_manager.get_active_companies()

        # Assert
        assert result == []
        mock_company_repository.find_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_companies_mixed_active_inactive(
        self, provider_manager, mock_company_repository
    ):
        """Test getting active companies when some companies are inactive."""
        # Arrange
        companies = [
            Company(
                name="Company A",
                provider_type=ProviderType.SERVICETITAN,
                provider_config={},
                is_active=True,
            ),
            Company(
                name="Company B",
                provider_type=ProviderType.HOUSECALLPRO,
                provider_config={},
                is_active=False,
            ),
            Company(
                name="Company C",
                provider_type=ProviderType.MOCK,
                provider_config={},
                is_active=True,
            ),
        ]
        mock_company_repository.find_active.return_value = companies

        # Act
        result = await provider_manager.get_active_companies()

        # Assert
        assert len(result) == 2  # Only active companies
        assert all(company.is_active for company in result)
        assert result[0].name == "Company A"
        assert result[1].name == "Company C"
