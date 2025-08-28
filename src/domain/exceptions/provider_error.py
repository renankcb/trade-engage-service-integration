"""
Provider-related domain exceptions.
"""


class ProviderError(Exception):
    """Base exception for provider-related errors."""

    pass


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is invalid."""

    pass


class ProviderAuthenticationError(ProviderError):
    """Raised when provider authentication fails."""

    pass


class ProviderAPIError(ProviderError):
    """Raised when provider API returns an error."""

    def __init__(self, provider: str, status_code: int, message: str):
        self.provider = provider
        self.status_code = status_code
        self.message = message
        super().__init__(f"Provider {provider} API error ({status_code}): {message}")


class ProviderRateLimitError(ProviderError):
    """Raised when provider rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int = None):
        self.provider = provider
        self.retry_after = retry_after
        message = f"Provider {provider} rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(message)


class ProviderNotFoundError(ProviderError):
    """Raised when provider type is not found."""

    def __init__(self, provider_type: str):
        self.provider_type = provider_type
        super().__init__(f"Provider type '{provider_type}' not found")
