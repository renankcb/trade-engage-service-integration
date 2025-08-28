"""
Unit tests for SyncJobUseCase.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.interfaces.providers import CreateLeadRequest, CreateLeadResponse
from src.application.use_cases.sync_job import SyncJobUseCase
from src.domain.entities.job import Job
from src.domain.entities.job_routing import JobRouting
from src.domain.exceptions.sync_error import SyncError, SyncStatusError
from src.domain.value_objects.address import Address
from src.domain.value_objects.provider_type import ProviderType
from src.domain.value_objects.sync_status import SyncStatus


class TestSyncJobUseCase:
    """Test cases for SyncJobUseCase."""

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
        )

    @pytest.fixture
    def sample_job_routing(self, sample_job):
        """Create a sample job routing for testing."""
        return JobRouting(job_id=sample_job.id, company_id_received=uuid4())

    @pytest.fixture
    def sample_company(self):
        """Create a sample company for testing."""
        company = MagicMock()
        company.id = uuid4()
        company.name = "Test Company"
        company.provider_type = ProviderType.SERVICETITAN
        company.provider_config = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "tenant_id": "test_tenant_id",
        }
        return company

    @pytest.fixture
    def mock_repositories(self, sample_job_routing, sample_job, sample_company):
        """Create mock repositories."""
        mock_job_routing_repo = AsyncMock()
        mock_job_routing_repo.get_by_id.return_value = sample_job_routing

        mock_job_repo = AsyncMock()
        mock_job_repo.get_by_id.return_value = sample_job

        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_id.return_value = sample_company

        return {
            "job_routing_repo": mock_job_routing_repo,
            "job_repo": mock_job_repo,
            "company_repo": mock_company_repo,
        }

    @pytest.fixture
    def mock_provider_manager(self):
        """Create mock provider manager."""
        mock_manager = MagicMock()
        mock_provider = AsyncMock()
        mock_provider.create_lead.return_value = CreateLeadResponse(
            success=True, external_id="ext_123"
        )
        mock_manager.get_provider.return_value = mock_provider

        return mock_manager

    @pytest.fixture
    def mock_data_transformer(self):
        """Create mock data transformer."""
        mock_transformer = MagicMock()
        mock_transformer.transform_job.return_value = {"transformed": "data"}

        return mock_transformer

    @pytest.fixture
    def use_case(self, mock_repositories, mock_provider_manager, mock_data_transformer):
        """Create SyncJobUseCase instance with mocked dependencies."""
        return SyncJobUseCase(
            job_routing_repo=mock_repositories["job_routing_repo"],
            job_repo=mock_repositories["job_repo"],
            company_repo=mock_repositories["company_repo"],
            provider_manager=mock_provider_manager,
            data_transformer=mock_data_transformer,
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self, use_case, sample_job_routing, mock_repositories
    ):
        """Test successful job sync execution."""
        # Arrange
        job_routing_id = sample_job_routing.id

        # Act
        result = await use_case.execute(job_routing_id)

        # Assert
        assert result is True

        # Verify job routing was updated
        mock_repositories["job_routing_repo"].update.assert_called_once()
        updated_routing = mock_repositories["job_routing_repo"].update.call_args[0][0]
        assert updated_routing.sync_status == SyncStatus.SYNCED
        assert updated_routing.external_id == "ext_123"

    @pytest.mark.asyncio
    async def test_execute_job_routing_not_found(self, use_case, mock_repositories):
        """Test execution when job routing is not found."""
        # Arrange
        mock_repositories["job_routing_repo"].get_by_id.return_value = None
        job_routing_id = uuid4()

        # Act & Assert
        with pytest.raises(SyncError, match=f"Job routing {job_routing_id} not found"):
            await use_case.execute(job_routing_id)

    @pytest.mark.asyncio
    async def test_execute_job_not_found(
        self, use_case, sample_job_routing, mock_repositories
    ):
        """Test execution when job is not found."""
        # Arrange
        mock_repositories["job_repo"].get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(
            SyncError, match=f"Job {sample_job_routing.job_id} not found"
        ):
            await use_case.execute(sample_job_routing.id)

    @pytest.mark.asyncio
    async def test_execute_company_not_found(
        self, use_case, sample_job_routing, sample_job, mock_repositories
    ):
        """Test execution when company is not found."""
        # Arrange
        mock_repositories["company_repo"].get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(
            SyncError,
            match=f"Company {sample_job_routing.company_id_received} not found",
        ):
            await use_case.execute(sample_job_routing.id)

    @pytest.mark.asyncio
    async def test_execute_sync_failed(
        self, use_case, sample_job_routing, mock_repositories, mock_provider_manager
    ):
        """Test execution when sync fails."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.create_lead.return_value = CreateLeadResponse(
            success=False, error_message="Provider error"
        )

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False

        # Verify job routing was marked as failed
        mock_repositories["job_routing_repo"].update.assert_called_once()
        updated_routing = mock_repositories["job_routing_repo"].update.call_args[0][0]
        assert updated_routing.sync_status == SyncStatus.FAILED
        assert updated_routing.error_message == "Provider error"

    @pytest.mark.asyncio
    async def test_execute_sync_status_error(
        self, use_case, sample_job_routing, mock_repositories
    ):
        """Test execution when sync status prevents sync."""
        # Arrange
        sample_job_routing.sync_status = SyncStatus.COMPLETED

        # Act & Assert
        with pytest.raises(SyncStatusError):
            await use_case.execute(sample_job_routing.id)

    @pytest.mark.asyncio
    async def test_execute_provider_exception(
        self, use_case, sample_job_routing, mock_provider_manager
    ):
        """Test execution when provider raises an exception."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.create_lead.side_effect = Exception("Provider connection failed")

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False

        # Verify job routing was marked as failed
        mock_repositories = use_case.job_routing_repo
        mock_repositories.update.assert_called_once()
        updated_routing = mock_repositories.update.call_args[0][0]
        assert updated_routing.sync_status == SyncStatus.FAILED
        assert "Provider connection failed" in updated_routing.error_message

    @pytest.mark.asyncio
    async def test_execute_without_external_id(
        self, use_case, sample_job_routing, mock_provider_manager
    ):
        """Test execution when provider response doesn't include external ID."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.create_lead.return_value = CreateLeadResponse(
            success=True, external_id=None
        )

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False

        # Verify job routing was marked as failed
        mock_repositories = use_case.job_routing_repo
        mock_repositories.update.assert_called_once()
        updated_routing = mock_repositories.update.call_args[0][0]
        assert updated_routing.sync_status == SyncStatus.FAILED
        assert "External ID is required" in updated_routing.error_message
