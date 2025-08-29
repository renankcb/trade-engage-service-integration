"""
ServiceTitan provider implementation.
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from src.application.interfaces.providers import (
    CreateLeadRequest,
    CreateLeadResponse,
    JobStatusResponse,
    ProviderHealthStatus,
    ProviderInterface,
)
from src.domain.entities.company import Company
from src.domain.exceptions.provider_error import (
    ProviderAPIError,
    ProviderConfigurationError,
)
from src.domain.value_objects.provider_type import ProviderType
from src.infrastructure.providers.servicetitan.client import ServiceTitanClient
from src.infrastructure.providers.servicetitan.transformer import (
    ServiceTitanTransformer,
)

logger = structlog.get_logger()


class ServiceTitanProvider(ProviderInterface):
    """ServiceTitan provider implementation."""

    @property
    def name(self) -> str:
        """Provider name."""
        return "ServiceTitan"

    def __init__(self, company: Company):
        self.company = company
        self.provider_type = ProviderType.SERVICETITAN

        # Validate configuration
        if not self._validate_config():
            raise ProviderConfigurationError("Invalid ServiceTitan configuration")

        # Initialize client and transformer
        self.client = ServiceTitanClient(
            client_id=self.company.provider_config["client_id"],
            client_secret=self.company.provider_config["client_secret"],
            tenant_id=self.company.provider_config["tenant_id"],
        )
        self.transformer = ServiceTitanTransformer()

    def _validate_config(self) -> bool:
        """Validate provider configuration."""
        required_fields = ["client_id", "client_secret", "tenant_id"]

        for field in required_fields:
            if field not in self.company.provider_config:
                logger.error(
                    "Missing required configuration field",
                    field=field,
                    company_id=str(self.company.id),
                )
                return False

        return True

    async def create_lead(self, request: CreateLeadRequest) -> CreateLeadResponse:
        """Create a lead in ServiceTitan."""
        try:
            logger.info(
                "Creating lead in ServiceTitan",
                company_id=str(self.company.id),
                job_summary=request.job.summary,
                idempotency_key=request.idempotency_key,
            )

            # Check if lead already exists using idempotency key
            existing_lead = await self._check_existing_lead(request.idempotency_key)
            if existing_lead:
                logger.info(
                    "Lead already exists in ServiceTitan",
                    company_id=str(self.company.id),
                    external_id=existing_lead.external_id,
                    idempotency_key=request.idempotency_key,
                )
                return CreateLeadResponse(
                    success=True,
                    external_id=existing_lead.external_id,
                    error_message=None,
                )

            # Transform domain data to ServiceTitan format
            st_lead_data = self.transformer.transform_lead_request(request)

            # Add idempotency key to ServiceTitan request
            st_lead_data["client_reference_id"] = request.idempotency_key

            # Create lead via API
            response = await self.client.create_lead(st_lead_data)

            # Transform response back to domain format
            lead_response = self.transformer.transform_lead_response(response)

            logger.info(
                "Lead created successfully in ServiceTitan",
                company_id=str(self.company.id),
                external_id=lead_response.external_id,
                idempotency_key=request.idempotency_key,
            )

            return lead_response

        except Exception as e:
            logger.error(
                "Failed to create lead in ServiceTitan",
                company_id=str(self.company.id),
                error=str(e),
                idempotency_key=request.idempotency_key,
            )

            return CreateLeadResponse(
                success=False, external_id=None, error_message=str(e)
            )

    async def _check_existing_lead(
        self, idempotency_key: str
    ) -> Optional[Dict[str, Any]]:
        """Check if a lead already exists using idempotency key."""
        try:
            # Search for existing lead by client_reference_id
            existing_leads = await self.client.search_leads(
                {"client_reference_id": idempotency_key}
            )

            if existing_leads and len(existing_leads) > 0:
                return existing_leads[0]

            return None

        except Exception as e:
            logger.warning(
                "Failed to check existing lead",
                company_id=str(self.company.id),
                idempotency_key=idempotency_key,
                error=str(e),
            )
            return None

    async def get_lead_status(self, external_id: str) -> dict:
        """Get lead status from ServiceTitan."""
        try:
            response = await self.client.get_lead(external_id)
            return self.transformer.transform_status_response(response)

        except Exception as e:
            logger.error(
                "Failed to get lead status from ServiceTitan",
                external_id=external_id,
                error=str(e),
            )
            raise ProviderAPIError(f"Failed to get lead status: {str(e)}")

    async def get_job_status(
        self, external_id: str, config: Dict[str, Any]
    ) -> JobStatusResponse:
        """Get status of a specific job from ServiceTitan."""
        try:
            logger.info(
                "Getting job status from ServiceTitan",
                company_id=str(self.company.id),
                external_id=external_id,
            )

            # Get lead status from ServiceTitan
            status_data = await self.get_lead_status(external_id)

            # Transform to JobStatusResponse format
            return JobStatusResponse(
                external_id=external_id,
                status=status_data.get("status", "unknown"),
                is_completed=status_data.get("is_completed", False),
                revenue=status_data.get("revenue"),
                completed_at=status_data.get("completed_at"),
                error_message=status_data.get("error_message"),
            )

        except Exception as e:
            logger.error(
                "Failed to get job status from ServiceTitan",
                external_id=external_id,
                error=str(e),
            )

            return JobStatusResponse(
                external_id=external_id,
                status="error",
                is_completed=False,
                revenue=None,
                completed_at=None,
                error_message=str(e),
            )

    async def batch_get_job_status(
        self, external_ids: List[str], config: Dict
    ) -> List[JobStatusResponse]:
        """Get status for multiple jobs in batch."""
        try:
            logger.info(
                "Batch getting job status from ServiceTitan",
                company_id=str(self.company.id),
                count=len(external_ids),
            )

            # Process in batches to avoid overwhelming the API
            batch_size = 10
            all_responses = []

            for i in range(0, len(external_ids), batch_size):
                batch = external_ids[i : i + batch_size]

                # Get status for this batch
                batch_responses = await self._get_batch_status(batch)
                all_responses.extend(batch_responses)

                # Small delay between batches to respect rate limits
                if i + batch_size < len(external_ids):
                    await asyncio.sleep(0.1)

            logger.info(
                "Batch job status completed",
                company_id=str(self.company.id),
                total_requested=len(external_ids),
                total_received=len(all_responses),
            )

            return all_responses

        except Exception as e:
            logger.error(
                "Failed to batch get job status from ServiceTitan",
                company_id=str(self.company.id),
                error=str(e),
            )
            raise ProviderAPIError(f"Failed to batch get job status: {str(e)}")

    async def _get_batch_status(
        self, external_ids: List[str]
    ) -> List[JobStatusResponse]:
        """Get status for a batch of external IDs."""
        responses = []

        for external_id in external_ids:
            try:
                status_response = await self.get_lead_status(external_id)
                responses.append(status_response)
            except Exception as e:
                logger.warning(
                    "Failed to get status for individual job",
                    external_id=external_id,
                    error=str(e),
                )
                # Create error response for this job
                error_response = JobStatusResponse(
                    external_id=external_id,
                    is_completed=False,
                    revenue=0.0,
                    completed_at=None,
                    error_message=str(e),
                )
                responses.append(error_response)

        return responses

    async def update_lead(self, external_id: str, update_data: dict) -> bool:
        """Update a lead in ServiceTitan."""
        try:
            st_update_data = self.transformer.transform_update_request(update_data)
            await self.client.update_lead(external_id, st_update_data)

            logger.info(
                "Lead updated successfully in ServiceTitan", external_id=external_id
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to update lead in ServiceTitan",
                external_id=external_id,
                error=str(e),
            )
            raise ProviderAPIError(f"Failed to update lead: {str(e)}")

    async def validate_config(self) -> bool:
        """Validate that the provider configuration is working."""
        try:
            # Test API connectivity
            await self.client.test_connection()
            return True

        except Exception as e:
            logger.error(
                "ServiceTitan configuration validation failed",
                company_id=str(self.company.id),
                error=str(e),
            )
            return False

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate provider configuration."""
        required_fields = ["client_id", "client_secret", "tenant_id"]

        for field in required_fields:
            if field not in config:
                logger.error("Missing required configuration field", field=field)
                return False

        return True

    async def get_health_status(self) -> ProviderHealthStatus:
        """Get provider health status."""
        try:
            # Test API connectivity
            response_time = await self.client.test_connection()

            return ProviderHealthStatus(
                is_healthy=True,
                last_check="2024-01-01T00:00:00Z",
                error_count=0,
                response_time_ms=response_time,
            )

        except Exception as e:
            logger.error(
                "ServiceTitan health check failed",
                company_id=str(self.company.id),
                error=str(e),
            )

            return ProviderHealthStatus(
                is_healthy=False,
                last_check="2024-01-01T00:00:00Z",
                error_count=1,
                response_time_ms=0,
            )
