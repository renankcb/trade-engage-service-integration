"""Job domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from src.domain.value_objects.address import Address


@dataclass
class Job:
    """Job domain entity."""

    summary: str
    address: Address
    homeowner_name: str
    homeowner_phone: Optional[str]
    homeowner_email: Optional[str]
    created_by_company_id: UUID
    created_by_technician_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"

    # Job skills and classification
    required_skills: Optional[list[str]] = None
    skill_levels: Optional[dict[str, str]] = None  # skill_name -> required_level
    category: Optional[str] = None

    def __post_init__(self):
        """Validate job data."""
        if not self.summary or not self.summary.strip():
            raise ValueError("Job summary is required")
        if not self.homeowner_name or not self.homeowner_name.strip():
            raise ValueError("Homeowner name is required")
        if not self.address:
            raise ValueError("Job address is required")

        # Set timestamps if not provided
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc)

    @property
    def location_string(self) -> str:
        """Get formatted location."""
        return self.address.full_address

    def can_be_routed(self) -> bool:
        """Check if job can be routed to service providers."""
        return bool(
            self.summary
            and self.address
            and self.homeowner_name
            and self.status == "pending"
            and self.created_by_company_id  # Deve ter empresa solicitante
            and self.created_by_technician_id  # Deve ter técnico identificador
        )

    def mark_completed(self, completed_at: Optional[datetime] = None) -> None:
        """Mark job as completed."""
        if self.status == "completed":
            raise ValueError("Job is already completed")

        self.status = "completed"
        self.completed_at = completed_at or datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_provider_format(self) -> dict:
        """Convert job to generic provider format."""
        return {
            "id": str(self.id),
            "description": self.summary,
            "customer_name": self.homeowner_name,
            "customer_phone": self.homeowner_phone,
            "customer_email": self.homeowner_email,
            "service_address": self.address.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
        }
