"""
Provider factory for creating provider instances.
"""

from typing import Dict, Type
from src.application.interfaces.providers import ProviderInterface
from src.domain.exceptions.provider_error import ProviderNotFoundError
from src.domain.value_objects.provider_type import ProviderType
from src.infrastructure.providers.mock.provider import MockProvider
from src.infrastructure.providers.servicetitan.provider import ServiceTitanProvider


class ProviderFactory:
    """Factory for creating provider instances."""
    
    def __init__(self):
        self._providers: Dict[ProviderType, Type[ProviderInterface]] = {
            ProviderType.MOCK: MockProvider,
            ProviderType.SERVICETITAN: ServiceTitanProvider,
        }
    
    def create_provider(
        self, 
        provider_type: ProviderType
    ) -> ProviderInterface:
        """Create a provider instance of the specified type."""
        provider_class = self._providers.get(provider_type)
        
        if not provider_class:
            raise ProviderNotFoundError(
                f"Provider type '{provider_type.value}' not supported"
            )
        
        return provider_class()
    
    def get_available_providers(self) -> list[ProviderType]:
        """Get list of available provider types."""
        return list(self._providers.keys())
    
    def register_provider(
        self, 
        provider_type: ProviderType, 
        provider_class: Type[ProviderInterface]
    ) -> None:
        """Register a new provider type."""
        self._providers[provider_type] = provider_class
    
    def has_provider(self, provider_type: ProviderType) -> bool:
        """Check if a provider type is available."""
        return provider_type in self._providers
