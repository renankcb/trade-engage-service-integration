"""
Unit tests for SyncJobUseCase.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.interfaces.providers import CreateLeadRequest, CreateLeadResponse
from src.application.services.transaction_service import TransactionService
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
        return JobRouting(
            job_id=sample_job.id,
            company_id_received=uuid4(),
            sync_status=SyncStatus.PENDING,
        )

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
        mock_job_routing_repo.update = AsyncMock()

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
    def mock_transaction_service(self):
        """Create mock transaction service."""
        mock_service = AsyncMock()
        mock_service.commit = AsyncMock()
        return mock_service

    @pytest.fixture
    def use_case(
        self,
        mock_repositories,
        mock_provider_manager,
        mock_data_transformer,
        mock_transaction_service,
    ):
        """Create SyncJobUseCase instance with mocked dependencies."""
        return SyncJobUseCase(
            job_routing_repo=mock_repositories["job_routing_repo"],
            job_repo=mock_repositories["job_repo"],
            company_repo=mock_repositories["company_repo"],
            provider_manager=mock_provider_manager,
            data_transformer=mock_data_transformer,
            transaction_service=mock_transaction_service,
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test successful job sync execution."""
        # Arrange
        job_routing_id = sample_job_routing.id

        # Act
        result = await use_case.execute(job_routing_id)

        # Assert
        assert result is True

        # Verify job routing was updated multiple times
        assert mock_repositories["job_routing_repo"].update.call_count >= 2

        # Verify transaction commits
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_job_routing_not_found(self, use_case, mock_repositories):
        """Test execution when job routing is not found."""
        # Arrange
        mock_repositories["job_routing_repo"].get_by_id.return_value = None
        job_routing_id = uuid4()

        # Act
        result = await use_case.execute(job_routing_id)

        # Assert
        assert result is False
        # Should not update anything since routing was not found
        mock_repositories["job_routing_repo"].update.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_job_not_found(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test execution when job is not found."""
        # Arrange
        mock_repositories["job_repo"].get_by_id.return_value = None

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        # Should attempt to update job routing with error
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_company_not_found(
        self,
        use_case,
        sample_job_routing,
        sample_job,
        mock_repositories,
        mock_transaction_service,
    ):
        """Test execution when company is not found."""
        # Arrange
        mock_repositories["company_repo"].get_by_id.return_value = None

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        # Should attempt to update job routing with error
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_sync_failed(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
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
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_sync_status_error(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test execution when sync status prevents sync."""
        # Arrange
        sample_job_routing.sync_status = SyncStatus.COMPLETED

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is True  # Should return True for already completed jobs
        # Should not update anything since job is already completed
        mock_repositories["job_routing_repo"].update.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_provider_exception(
        self,
        use_case,
        sample_job_routing,
        mock_provider_manager,
        mock_transaction_service,
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
        mock_repositories.update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_without_external_id(
        self,
        use_case,
        sample_job_routing,
        mock_provider_manager,
        mock_transaction_service,
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
        mock_repositories.update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_already_synced_status(
        self, use_case, sample_job_routing, mock_repositories
    ):
        """Test execution when job routing is already synced."""
        # Arrange
        sample_job_routing.sync_status = SyncStatus.SYNCED
        sample_job_routing.external_id = "ext_123"

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is True
        # Should not update or commit anything
        mock_repositories["job_routing_repo"].update.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_already_completed_status(
        self, use_case, sample_job_routing, mock_repositories
    ):
        """Test execution when job routing is already completed."""
        # Arrange
        sample_job_routing.sync_status = SyncStatus.COMPLETED

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is True
        # Should not update or commit anything
        mock_repositories["job_routing_repo"].update.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_failed_status_with_retry_available(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when job routing is failed but retry is available."""
        # Arrange
        sample_job_routing.sync_status = SyncStatus.FAILED
        sample_job_routing.retry_count = 1
        sample_job_routing.next_retry_at = datetime.now(timezone.utc) - timedelta(
            minutes=1
        )

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is True
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_failed_status_no_retry_available(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test execution when job routing is failed and no retry is available."""
        # Arrange
        sample_job_routing.sync_status = SyncStatus.FAILED
        sample_job_routing.retry_count = 3
        sample_job_routing.next_retry_at = None

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        # Should attempt to update job routing with error
        mock_repositories["job_routing_repo"].update.assert_called()
        # Only 1 commit since the error is caught and handled
        assert mock_transaction_service.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_processing_status_stuck(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when job routing is processing but stuck."""
        # Arrange
        sample_job_routing.sync_status = SyncStatus.PROCESSING
        sample_job_routing.updated_at = datetime.now(timezone.utc) - timedelta(
            minutes=15
        )  # Stuck for 15 minutes

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is True
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_processing_status_not_stuck(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test execution when job routing is processing but not stuck."""
        # Arrange
        sample_job_routing.sync_status = SyncStatus.PROCESSING
        sample_job_routing.updated_at = datetime.now(timezone.utc) - timedelta(
            minutes=5
        )  # Only 5 minutes old

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        # Should attempt to update job routing with error
        mock_repositories["job_routing_repo"].update.assert_called()
        # Only 1 commit since the error is caught and handled
        assert mock_transaction_service.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_mark_processing_fails(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test execution when marking as processing fails."""
        # Arrange
        mock_repositories["job_routing_repo"].update.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        # Should not commit anything since marking as processing failed
        mock_transaction_service.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_fresh_routing_not_found(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test execution when fresh routing is not found after marking as processing."""
        # Arrange
        # First call returns routing, second call returns None
        mock_repositories["job_routing_repo"].get_by_id.side_effect = [
            sample_job_routing,  # First call
            None,  # Second call (after marking as processing)
        ]

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        mock_transaction_service.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_provider_response_success_with_external_id(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test successful provider response with external ID."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.create_lead.return_value = CreateLeadResponse(
            success=True, external_id="ext_456"
        )

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is True
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_provider_response_failure_with_error_message(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test provider response failure with error message."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.create_lead.return_value = CreateLeadResponse(
            success=False, error_message="Invalid configuration"
        )

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_provider_response_failure_without_error_message(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test provider response failure without error message."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.create_lead.return_value = CreateLeadResponse(
            success=False, error_message=None
        )

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_exception_handling(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test exception handling during execution."""
        # Arrange
        mock_repositories["job_repo"].get_by_id.side_effect = Exception(
            "Database connection failed"
        )

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        # Should attempt to update job routing with error
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_exception_during_update_after_error(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test exception handling when updating job routing after error fails."""
        # Arrange
        mock_repositories["job_repo"].get_by_id.side_effect = Exception(
            "Database connection failed"
        )
        # Update after error also fails
        mock_repositories["job_routing_repo"].update.side_effect = [
            None,  # First update (mark as processing) succeeds
            Exception("Update failed"),  # Second update (after error) fails
        ]

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        assert result is False
        # Should still attempt to update
        assert mock_repositories["job_routing_repo"].update.call_count >= 1

    @pytest.mark.asyncio
    async def test_execute_idempotency_key_usage(
        self, use_case, sample_job_routing, mock_provider_manager
    ):
        """Test that idempotency key is used in CreateLeadRequest."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value

        # Act
        await use_case.execute(sample_job_routing.id)

        # Assert
        mock_provider.create_lead.assert_called_once()
        call_args = mock_provider.create_lead.call_args[0][0]
        assert isinstance(call_args, CreateLeadRequest)
        assert call_args.idempotency_key == str(sample_job_routing.id)

    @pytest.mark.asyncio
    async def test_execute_provider_manager_integration(
        self, use_case, sample_job_routing, sample_company, mock_provider_manager
    ):
        """Test integration with provider manager."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value

        # Act
        await use_case.execute(sample_job_routing.id)

        # Assert
        mock_provider_manager.get_provider.assert_called_once_with(
            sample_company.provider_type, company=sample_company
        )

    @pytest.mark.asyncio
    async def test_execute_logging_verification(
        self, use_case, sample_job_routing, sample_company, mock_provider_manager
    ):
        """Test that appropriate logging occurs during execution."""
        # Arrange
        with patch("src.application.use_cases.sync_job.logger") as mock_logger:
            # Act
            await use_case.execute(sample_job_routing.id)

            # Assert
            # Should log job sync started
            mock_logger.info.assert_called()
            # Check for specific log message
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Job sync started" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_execute_transaction_service_integration(
        self, use_case, sample_job_routing, mock_transaction_service
    ):
        """Test integration with transaction service."""
        # Act
        await use_case.execute(sample_job_routing.id)

        # Assert
        # Should commit multiple times during execution
        assert mock_transaction_service.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_race_condition_prevention(
        self, use_case, sample_job_routing, mock_repositories, mock_transaction_service
    ):
        """Test that race conditions are prevented by double-checking status."""
        # Arrange
        # First call returns original routing, second call returns fresh routing
        original_routing = JobRouting(
            job_id=sample_job_routing.job_id,
            company_id_received=sample_job_routing.company_id_received,
            sync_status=SyncStatus.PENDING,
        )
        fresh_routing = JobRouting(
            job_id=sample_job_routing.job_id,
            company_id_received=sample_job_routing.company_id_received,
            sync_status=SyncStatus.PROCESSING,  # Status changed by another process
        )

        mock_repositories["job_routing_repo"].get_by_id.side_effect = [
            original_routing,  # First call
            fresh_routing,  # Second call
        ]

        # Act
        result = await use_case.execute(sample_job_routing.id)

        # Assert
        # Should use fresh routing data
        assert result is True
        mock_repositories["job_routing_repo"].update.assert_called()
        assert mock_transaction_service.commit.call_count >= 2
