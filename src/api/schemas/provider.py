"""
Provider-related API schemas."""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel

from src.domain.value_objects.provider_type import ProviderType

from .common import TimestampMixin


class ProviderConfigSchema(BaseModel):
    """Provider configuration schema."""

    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    webhook_secret: Optional[str] = None


class CompanyResponse(TimestampMixin):
    """Company response schema."""

    id: UUID
    name: str
    provider_type: ProviderType
    is_active: bool

    model_config = {"from_attributes": True}


class ProviderResponse(BaseModel):
    """Provider response schema."""

    type: ProviderType
    display_name: str
    requires_auth: bool
    supports_webhooks: bool
    is_configured: bool


class WebhookPayload(BaseModel):
    """Generic webhook payload schema."""

    provider: str
    event_type: str
    external_id: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None
    signature: Optional[str] = None
