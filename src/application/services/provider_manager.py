"""
Provider manager service for handling provider operations.
"""

from typing import List, Optional
from uuid import UUID

import structlog

from src.application.interfaces.providers import (
    CreateLeadRequest,
    CreateLeadResponse,
    ProviderInterface,
)
from src.application.interfaces.repositories import CompanyRepositoryInterface
from src.background.workers.rate_limiter import RateLimiterInterface
from src.background.workers.retry_handler import RetryHandlerInterface
from src.domain.entities.company import Company
from src.domain.exceptions.provider_error import (
    ProviderAPIError,
    ProviderConfigurationError,
)
from src.domain.value_objects.provider_type import ProviderType

logger = structlog.get_logger()


class ProviderManager:
    """Manages provider operations and integrations."""

    def __init__(
        self,
        provider_factory,
        company_repository: CompanyRepositoryInterface,
        rate_limiter: Optional[RateLimiterInterface] = None,
        retry_handler: Optional[RetryHandlerInterface] = None,
    ):
        self.provider_factory = provider_factory
        self.company_repository = company_repository
        self.rate_limiter = rate_limiter
        self.retry_handler = retry_handler

    async def get_provider_for_company(
        self, company_id: UUID
    ) -> Optional[ProviderInterface]:
        """Get the appropriate provider for a company."""
        try:
            company = await self.company_repository.get_by_id(company_id)
            if not company:
                logger.warning("Company not found", company_id=str(company_id))
                return None

            provider_type = company.provider_type
            provider = self.provider_factory.get_provider(provider_type)
            if not provider:
                logger.error(
                    "Provider not found for company",
                    company_id=str(company_id),
                    provider_type=provider_type.value,
                )
                return None

            return provider

        except Exception as e:
            logger.error(
                "Error getting provider for company",
                company_id=str(company_id),
                error=str(e),
            )
            return None

    def get_provider(self, provider_type: ProviderType, **kwargs) -> ProviderInterface:
        """Get provider by type (synchronous method for use cases)."""
        provider = self.provider_factory.create_provider(provider_type, **kwargs)
        if not provider:
            raise ProviderConfigurationError(
                f"Provider {provider_type.value} not found"
            )
        return provider

    async def create_lead(
        self,
        company_id: UUID,
        lead_data: CreateLeadRequest,
    ) -> Optional[CreateLeadResponse]:
        """Create a lead using the appropriate provider."""
        try:
            provider = await self.get_provider_for_company(company_id)
            if not provider:
                raise ProviderConfigurationError(
                    f"No provider found for company {company_id}"
                )

            # Check rate limiting
            if self.rate_limiter:
                await self.rate_limiter.check_rate_limit(f"create_lead:{company_id}")

            # Create lead with retry logic
            if self.retry_handler:
                response = await self.retry_handler.execute_with_retry(
                    lambda: provider.create_lead(lead_data)
                )
            else:
                response = await provider.create_lead(lead_data)

            logger.info(
                "Lead created successfully",
                company_id=str(company_id),
                external_id=response.external_id,
            )

            return response

        except ProviderAPIError as e:
            logger.error(
                "Provider API error creating lead",
                company_id=str(company_id),
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error creating lead",
                company_id=str(company_id),
                error=str(e),
            )
            raise ProviderAPIError("unknown", 0, f"Failed to create lead: {str(e)}")

    async def get_active_companies(
        self, provider_type: Optional[ProviderType] = None
    ) -> List[Company]:
        """Get active companies, optionally filtered by provider type."""
        try:
            if provider_type:
                companies = await self.company_repository.find_by_provider_type(
                    provider_type
                )
            else:
                companies = await self.company_repository.find_active()

            return [c for c in companies if c.is_active]

        except Exception as e:
            logger.error(
                "Error getting active companies",
                provider_type=provider_type.value if provider_type else None,
                error=str(e),
            )
            return []

    async def validate_provider_config(self, company_id: UUID) -> bool:
        """Validate that a company's provider configuration is correct."""
        try:
            provider = await self.get_provider_for_company(company_id)
            if not provider:
                return False

            # Test provider connectivity
            is_valid = await provider.validate_config()

            logger.info(
                "Provider config validation result",
                company_id=str(company_id),
                is_valid=is_valid,
            )

            return is_valid

        except Exception as e:
            logger.error(
                "Provider config validation failed",
                company_id=str(company_id),
                error=str(e),
            )
            return False

    async def get_provider_status(self, company_id: UUID) -> dict:
        """Get the status of a company's provider integration."""
        try:
            provider = await self.get_provider_for_company(company_id)
            if not provider:
                return {"status": "no_provider", "error": "Provider not found"}

            # Get provider health status
            health_status = await provider.get_health_status()

            return {
                "status": "healthy" if health_status.is_healthy else "unhealthy",
                "provider_type": provider.provider_type.value,
                "last_check": health_status.last_check,
                "response_time_ms": health_status.response_time_ms,
            }

        except Exception as e:
            logger.error(
                "Error getting provider status",
                company_id=str(company_id),
                error=str(e),
            )
            return {"status": "error", "error": str(e)}
