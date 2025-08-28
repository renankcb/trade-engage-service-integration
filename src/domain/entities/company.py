"""Company domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from src.domain.value_objects.provider_type import ProviderType


@dataclass
class Company:
    """Company domain entity."""

    name: str
    provider_type: ProviderType
    provider_config: Dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate company data."""
        if not self.name or not self.name.strip():
            raise ValueError("Company name is required")

    def is_provider_configured(self) -> bool:
        """Check if provider is properly configured."""
        if not self.provider_type.requires_auth:
            return True

        required_fields = {
            ProviderType.SERVICETITAN: ["client_id", "client_secret", "tenant_id"],
            ProviderType.HOUSECALLPRO: ["api_key", "company_id"],
        }

        required = required_fields.get(self.provider_type, [])
        return all(field in self.provider_config for field in required)

    def get_provider_credential(self, key: str) -> Optional[str]:
        """Safely get provider credential."""
        return self.provider_config.get(key)

    def update_provider_config(self, new_config: Dict[str, Any]) -> None:
        """Update provider configuration."""
        self.provider_config.update(new_config)

    def can_receive_jobs(self) -> bool:
        """Check if company can receive job routings."""
        return (
            self.is_active
            and self.is_provider_configured()
            and self.provider_type != ProviderType.MOCK
        )
