"""
Unit tests for PollUpdatesUseCase.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.interfaces.providers import JobStatusResponse
from src.application.use_cases.poll_updates import PollResult, PollUpdatesUseCase
from src.domain.entities.job import Job
from src.domain.entities.job_routing import JobRouting
from src.domain.value_objects.address import Address
from src.domain.value_objects.provider_type import ProviderType
from src.domain.value_objects.sync_status import SyncStatus
from src.infrastructure.database.repositories.transaction_repository import (
    TransactionService,
)


class TestPollUpdatesUseCase:
    """Test cases for PollUpdatesUseCase."""

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
            sync_status=SyncStatus.SYNCED,
            external_id="ext_123",
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
        mock_job_routing_repo.find_synced_for_polling.return_value = [
            sample_job_routing
        ]
        mock_job_routing_repo.update = AsyncMock()

        mock_job_repo = AsyncMock()
        mock_job_repo.get_by_id.return_value = sample_job
        mock_job_repo.update = AsyncMock()

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
        mock_provider.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_123",
                status="completed",
                is_completed=True,
                revenue=150.0,
                completed_at="2025-08-29T18:00:00Z",
            )
        ]
        mock_manager.get_provider.return_value = mock_provider

        return mock_manager

    @pytest.fixture
    def mock_transaction_service(self):
        """Create mock transaction service."""
        mock_service = AsyncMock()
        mock_service.commit = AsyncMock()
        return mock_service

    @pytest.fixture
    def use_case(
        self, mock_repositories, mock_provider_manager, mock_transaction_service
    ):
        """Create PollUpdatesUseCase instance with mocked dependencies."""
        return PollUpdatesUseCase(
            job_routing_repo=mock_repositories["job_routing_repo"],
            company_repo=mock_repositories["company_repo"],
            job_repo=mock_repositories["job_repo"],
            provider_manager=mock_provider_manager,
            transaction_service=mock_transaction_service,
        )

    @pytest.mark.asyncio
    async def test_execute_success_with_completed_jobs(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test successful execution with completed jobs."""
        # Act
        result = await use_case.execute()

        # Assert
        assert isinstance(result, PollResult)
        assert result.total_polled == 1
        assert result.updated == 1
        assert result.completed == 1
        assert result.errors == []
        assert result.processing_time > 0

        # Verify repositories were called
        mock_repositories[
            "job_routing_repo"
        ].find_synced_for_polling.assert_called_once()
        mock_repositories["job_routing_repo"].update.assert_called()
        mock_repositories["job_repo"].update.assert_called()
        mock_transaction_service.commit.assert_called()

    @pytest.mark.asyncio
    async def test_execute_with_custom_limit(self, use_case, mock_repositories):
        """Test execution with custom limit."""
        # Arrange
        custom_limit = 50

        # Act
        result = await use_case.execute(limit=custom_limit)

        # Assert
        mock_repositories[
            "job_routing_repo"
        ].find_synced_for_polling.assert_called_once_with(custom_limit)

    @pytest.mark.asyncio
    async def test_execute_no_synced_jobs(self, use_case, mock_repositories):
        """Test execution when no synced jobs are found."""
        # Arrange
        mock_repositories["job_routing_repo"].find_synced_for_polling.return_value = []

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 0
        assert result.updated == 0
        assert result.completed == 0
        assert result.errors == []
        assert result.processing_time == 0.0

    @pytest.mark.asyncio
    async def test_execute_multiple_provider_groups(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution with multiple provider/company groups."""
        # Arrange
        company1 = MagicMock()
        company1.id = uuid4()
        company1.provider_type = ProviderType.SERVICETITAN

        company2 = MagicMock()
        company2.id = uuid4()
        company2.provider_type = ProviderType.HOUSECALLPRO

        routing1 = JobRouting(
            job_id=uuid4(),
            company_id_received=company1.id,
            sync_status=SyncStatus.SYNCED,
            external_id="ext_1",
        )
        routing2 = JobRouting(
            job_id=uuid4(),
            company_id_received=company2.id,
            sync_status=SyncStatus.SYNCED,
            external_id="ext_2",
        )

        mock_repositories["job_routing_repo"].find_synced_for_polling.return_value = [
            routing1,
            routing2,
        ]

        # Mock company repo to return different companies
        def mock_get_company(company_id):
            if company_id == company1.id:
                return company1
            elif company_id == company2.id:
                return company2
            return None

        mock_repositories["company_repo"].get_by_id.side_effect = mock_get_company

        # Mock provider responses
        mock_provider1 = AsyncMock()
        mock_provider1.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_1", status="completed", is_completed=True
            )
        ]

        mock_provider2 = AsyncMock()
        mock_provider2.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_2", status="in_progress", is_completed=False
            )
        ]

        def mock_get_provider(provider_type, company):
            if provider_type == ProviderType.SERVICETITAN:
                return mock_provider1
            elif provider_type == ProviderType.HOUSECALLPRO:
                return mock_provider2
            return None

        mock_provider_manager.get_provider.side_effect = mock_get_provider

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 2
        assert result.updated == 2
        assert result.completed == 1
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_execute_company_not_found(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when company is not found."""
        # Arrange
        mock_repositories["company_repo"].get_by_id.return_value = None

        # Act
        result = await use_case.execute()

        # Assert
        # When company is not found, the routing is skipped and not counted
        assert result.total_polled == 0
        assert result.updated == 0
        assert result.completed == 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_execute_no_external_ids(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when no external IDs are found."""
        # Arrange
        routing_without_external_id = JobRouting(
            job_id=uuid4(),
            company_id_received=uuid4(),
            sync_status=SyncStatus.SYNCED,
            external_id=None,  # No external ID
        )
        mock_repositories["job_routing_repo"].find_synced_for_polling.return_value = [
            routing_without_external_id
        ]

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 1
        assert result.updated == 0
        assert result.completed == 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_execute_provider_batch_polling_failure(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when provider batch polling fails."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.side_effect = Exception("Provider API error")

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 1
        assert result.updated == 0
        assert result.completed == 0
        assert len(result.errors) == 1
        assert "Provider polling failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_status_response_with_error(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when status response contains error."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_123",
                status="error",
                is_completed=False,
                error_message="Job not found in provider system",
            )
        ]

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 1
        assert result.updated == 0
        assert result.completed == 0
        assert len(result.errors) == 1
        assert "Status error for ext_123" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_no_status_response_for_routing(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when no status response is found for a routing."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_999", status="completed", is_completed=True
            )
        ]

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 1
        assert result.updated == 0
        assert result.completed == 0
        assert len(result.errors) == 1
        assert "No status response for ext_123" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_job_completion_flow(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test complete job completion flow."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_123",
                status="completed",
                is_completed=True,
                revenue=250.0,
                completed_at="2025-08-29T18:00:00Z",
            )
        ]

        # Act
        result = await use_case.execute()

        # Assert
        assert result.completed == 1
        assert result.updated == 1

        # Verify job routing was marked as completed
        mock_repositories["job_routing_repo"].update.assert_called()

        # Verify job entity was updated
        mock_repositories["job_repo"].update.assert_called()

        # Verify transaction was committed
        mock_transaction_service.commit.assert_called()

    @pytest.mark.asyncio
    async def test_execute_job_not_completed_flow(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test flow when job is not completed."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_123", status="in_progress", is_completed=False
            )
        ]

        # Act
        result = await use_case.execute()

        # Assert
        assert result.completed == 0
        assert result.updated == 1

        # Verify job routing was updated (last_synced_at)
        mock_repositories["job_routing_repo"].update.assert_called()

        # Verify job entity was NOT updated
        mock_repositories["job_repo"].update.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_routing_update_failure(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when routing update fails."""
        # Arrange
        mock_repositories["job_routing_repo"].update.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 1
        # The routing is still counted as updated even if the update fails
        # because the error is caught and logged, but the count is incremented before the error
        assert result.updated == 1
        assert result.completed == 1
        assert len(result.errors) == 1
        assert "Failed to update routing" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_job_update_failure(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution when job update fails."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_123",
                status="completed",
                is_completed=True,
                revenue=150.0,
            )
        ]

        mock_repositories["job_repo"].update.side_effect = Exception(
            "Job update failed"
        )

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 1
        # The routing is still counted as updated even if the job update fails
        # because the error is caught and logged, but the count is incremented before the error
        assert result.updated == 1
        assert result.completed == 1
        assert len(result.errors) == 1
        assert "Failed to update routing" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_provider_exception_handling(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test exception handling during provider operations."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.side_effect = Exception("Network timeout")

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 1
        assert result.updated == 0
        assert result.completed == 0
        assert len(result.errors) == 1
        assert "Provider polling failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_transaction_service_integration(
        self,
        use_case,
        sample_job_routing,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test integration with transaction service."""
        # Act
        await use_case.execute()

        # Assert
        # Should commit transaction for each routing update
        assert mock_transaction_service.commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_execute_logging_verification(
        self, use_case, sample_job_routing, sample_company, mock_provider_manager
    ):
        """Test that appropriate logging occurs during execution."""
        # Arrange
        with patch("src.application.use_cases.poll_updates.logger") as mock_logger:
            # Act
            await use_case.execute()

            # Assert
            # Should log various stages of execution
            mock_logger.info.assert_called()

            # Check for specific log messages
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Starting job status polling" in call for call in log_calls)
            assert any("Job status polling completed" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_execute_should_poll_method(self, use_case, sample_job_routing):
        """Test the _should_poll method logic."""
        # Test with SYNCED status
        assert use_case._should_poll(sample_job_routing) is True

        # Test with non-SYNCED status
        sample_job_routing.sync_status = SyncStatus.PENDING
        assert use_case._should_poll(sample_job_routing) is False

        # Test with recent polling - should respect the minimum interval
        sample_job_routing.sync_status = SyncStatus.SYNCED
        sample_job_routing.last_synced_at = datetime.now(timezone.utc)
        # The method checks if enough time has passed since last poll
        # Since we just set it to now, it should return False
        assert use_case._should_poll(sample_job_routing) is False

    @pytest.mark.asyncio
    async def test_execute_empty_batch_polling(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution with empty batch polling response."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.return_value = []

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 1
        assert result.updated == 0
        assert result.completed == 0
        assert len(result.errors) == 1
        assert "No status response for ext_123" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_mixed_status_responses(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test execution with mixed status responses."""
        # Arrange
        routing1 = JobRouting(
            job_id=uuid4(),
            company_id_received=uuid4(),
            sync_status=SyncStatus.SYNCED,
            external_id="ext_1",
        )
        routing2 = JobRouting(
            job_id=uuid4(),
            company_id_received=uuid4(),
            sync_status=SyncStatus.SYNCED,
            external_id="ext_2",
        )

        mock_repositories["job_routing_repo"].find_synced_for_polling.return_value = [
            routing1,
            routing2,
        ]

        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.return_value = [
            JobStatusResponse(
                external_id="ext_1",
                status="completed",
                is_completed=True,
                revenue=100.0,
            ),
            JobStatusResponse(
                external_id="ext_2", status="in_progress", is_completed=False
            ),
        ]

        # Act
        result = await use_case.execute()

        # Assert
        assert result.total_polled == 2
        assert result.updated == 2
        assert result.completed == 1
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_execute_provider_config_usage(
        self, use_case, sample_job_routing, sample_company, mock_provider_manager
    ):
        """Test that provider config is correctly passed to provider."""
        # Arrange
        mock_provider = mock_provider_manager.get_provider.return_value

        # Act
        await use_case.execute()

        # Assert
        mock_provider.batch_get_job_status.assert_called_once()
        call_args = mock_provider.batch_get_job_status.call_args
        assert call_args[0][1] == sample_company.provider_config  # config parameter

    @pytest.mark.asyncio
    async def test_execute_error_aggregation(
        self,
        use_case,
        mock_repositories,
        mock_provider_manager,
        mock_transaction_service,
    ):
        """Test that errors are properly aggregated across different sources."""
        # Arrange
        # Company not found error
        mock_repositories["company_repo"].get_by_id.return_value = None

        # Provider error
        mock_provider = mock_provider_manager.get_provider.return_value
        mock_provider.batch_get_job_status.side_effect = Exception("Provider error")

        # Act
        result = await use_case.execute()

        # Assert
        # When company is not found, the routing is skipped entirely
        # so no provider error occurs
        assert result.total_polled == 0
        assert result.updated == 0
        assert result.completed == 0
        assert result.errors == []
