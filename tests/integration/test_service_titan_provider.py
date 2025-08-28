"""Integration tests for ServiceTitan provider."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from src.application.interfaces.providers import CreateLeadRequest
from src.domain.entities.job import Job
from src.domain.exceptions.provider_error import ProviderAPIError
from src.domain.value_objects.address import Address
from src.infrastructure.providers.servicetitan.auth import ServiceTitanAuth
from src.infrastructure.providers.servicetitan.client import ServiceTitanClient
from src.infrastructure.providers.servicetitan.provider import ServiceTitanProvider


@pytest.mark.integration
class TestServiceTitanProvider:
    """Integration tests for ServiceTitan provider."""

    @pytest_asyncio.fixture
    async def provider(self):
        """Create ServiceTitan provider instance."""
        return ServiceTitanProvider()

    @pytest_asyncio.fixture
    def sample_job(self):
        """Create sample job for testing."""
        address = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )

        return Job(
            id=uuid4(),
            summary="Kitchen faucet replacement needed",
            address=address,
            homeowner_name="John Doe",
            homeowner_phone="(555) 123-4567",
            homeowner_email="john@example.com",
            created_by_company_id=uuid4(),
            created_by_technician_id=uuid4(),
        )

    @pytest_asyncio.fixture
    def sample_config(self):
        """Create sample company config."""
        return {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "tenant_id": "12345",
            "business_unit_id": 1,
            "default_job_type_id": 2,
        }

    @pytest.mark.asyncio
    async def test_create_lead_success(self, provider, sample_job, sample_config):
        """Test successful lead creation."""
        with patch.object(
            provider.client, "create_customer"
        ) as mock_customer, patch.object(
            provider.client, "create_location"
        ) as mock_location, patch.object(
            provider.client, "create_job"
        ) as mock_job:
            # Mock responses
            mock_customer.return_value = {
                "id": 123,
                "firstName": "John",
                "lastName": "Doe",
            }
            mock_location.return_value = {"id": 456, "customerId": 123}
            mock_job.return_value = {"id": 789, "jobNumber": "J-789"}

            # Execute
            request = CreateLeadRequest(job=sample_job, company_config=sample_config)
            response = await provider.create_lead(request)

            # Verify
            assert response.success is True
            assert response.external_id == "789"
            assert response.error_message is None

            # Verify API calls were made
            mock_customer.assert_called_once()
            mock_location.assert_called_once()
            mock_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_lead_customer_creation_fails(
        self, provider, sample_job, sample_config
    ):
        """Test lead creation when customer creation fails."""
        with patch.object(provider.client, "create_customer") as mock_customer:
            mock_customer.side_effect = ProviderAPIError(
                "servicetitan", 400, "Invalid customer data"
            )

            request = CreateLeadRequest(job=sample_job, company_config=sample_config)
            response = await provider.create_lead(request)

            assert response.success is False
            assert "Invalid customer data" in response.error_message

    @pytest.mark.asyncio
    async def test_get_job_status_success(self, provider, sample_config):
        """Test successful job status retrieval."""
        with patch.object(provider.client, "get_job") as mock_get_job:
            mock_get_job.return_value = {
                "id": 789,
                "status": "Completed",
                "total": 250.00,
                "completedOn": "2024-01-01T12:00:00Z",
            }

            response = await provider.get_job_status("789", sample_config)

            assert response.external_id == "789"
            assert response.status == "completed"
            assert response.is_completed is True
            assert response.revenue == 250.00

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, provider, sample_config):
        """Test job status when job not found."""
        with patch.object(provider.client, "get_job") as mock_get_job:
            mock_get_job.side_effect = ProviderAPIError(
                "servicetitan", 404, "Job not found"
            )

            response = await provider.get_job_status("999", sample_config)

            assert response.external_id == "999"
            assert response.status == "error"
            assert response.is_completed is False
            assert "Job not found" in response.error_message

    @pytest.mark.asyncio
    async def test_batch_get_job_status(self, provider, sample_config):
        """Test batch job status retrieval."""
        external_ids = ["789", "790", "791"]

        with patch.object(provider, "get_job_status") as mock_get_status:
            # Mock individual status calls
            mock_get_status.side_effect = [
                MagicMock(external_id="789", status="completed", is_completed=True),
                MagicMock(external_id="790", status="in_progress", is_completed=False),
                MagicMock(external_id="791", status="scheduled", is_completed=False),
            ]

            responses = await provider.batch_get_job_status(external_ids, sample_config)

            assert len(responses) == 3
            assert responses[0].external_id == "789"
            assert responses[1].external_id == "790"
            assert responses[2].external_id == "791"

    @pytest.mark.asyncio
    async def test_validate_config_valid(self, provider):
        """Test config validation with valid config."""
        config = {
            "client_id": "test_id",
            "client_secret": "test_secret",
            "tenant_id": "12345",
        }

        assert provider.validate_config(config) is True

    @pytest.mark.asyncio
    async def test_validate_config_missing_fields(self, provider):
        """Test config validation with missing fields."""
        config = {
            "client_id": "test_id",
            # Missing client_secret and tenant_id
        }

        assert provider.validate_config(config) is False

    @pytest.mark.asyncio
    async def test_provider_name(self, provider):
        """Test provider name property."""
        assert provider.name == "ServiceTitan"
