"""
Provider type value object.
"""

from enum import Enum


class ProviderType(str, Enum):
    """Provider type enumeration."""

    SERVICETITAN = "servicetitan"
    HOUSECALLPRO = "housecallpro"
    MOCK = "mock"

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return {
            self.SERVICETITAN: "ServiceTitan",
            self.HOUSECALLPRO: "HousecallPro",
            self.MOCK: "Mock Provider",
        }.get(self, self.value.title())

    @property
    def requires_auth(self) -> bool:
        """Check if provider requires authentication."""
        return self != self.MOCK

    @property
    def supports_webhooks(self) -> bool:
        """Check if provider supports webhooks."""
        return {self.SERVICETITAN: False, self.HOUSECALLPRO: True, self.MOCK: True}.get(
            self, False
        )
