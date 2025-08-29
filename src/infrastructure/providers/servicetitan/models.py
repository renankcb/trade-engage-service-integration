"""
ServiceTitan data models and DTOs.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ServiceTitanLeadRequest:
    """ServiceTitan lead creation request."""

    summary: str
    customer_name: str
    customer_phone: str
    customer_email: str
    address: str
    city: str
    state: str
    zip_code: str
    priority: str = "normal"
    notes: Optional[str] = None


@dataclass
class ServiceTitanLeadResponse:
    """ServiceTitan lead creation response."""

    id: str
    status: str
    created_at: str
    customer_id: str
    location_id: str


@dataclass
class ServiceTitanCustomerRequest:
    """ServiceTitan customer creation request."""

    name: str
    phone: str
    email: str
    address: str
    city: str
    state: str
    zip_code: str


@dataclass
class ServiceTitanLocationRequest:
    """ServiceTitan location creation request."""

    customer_id: str
    address: str
    city: str
    state: str
    zip_code: str
    address_type: str = "service"


@dataclass
class ServiceTitanJobRequest:
    """ServiceTitan job creation request."""

    customer_id: str
    location_id: str
    summary: str
    priority: str = "normal"
    notes: Optional[str] = None
    scheduled_date: Optional[str] = None


@dataclass
class ServiceTitanJobResponse:
    """ServiceTitan job creation response."""

    id: str
    status: str
    created_at: str
    customer_id: str
    location_id: str
    summary: str


@dataclass
class ServiceTitanStatusResponse:
    """ServiceTitan job status response."""

    id: str
    status: str
    is_completed: bool
    revenue: Optional[float] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ServiceTitanErrorResponse:
    """ServiceTitan error response."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
