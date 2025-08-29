"""
Technician domain entity.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from src.domain.value_objects.address import Address


class Technician:
    """Technician entity representing a service technician."""

    def __init__(
        self,
        id: UUID,
        name: str,
        phone: str,
        email: str,
        company_id: UUID,
        address: Optional[Address] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.phone = phone
        self.email = email
        self.company_id = company_id
        self.address = address
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def update_contact_info(self, phone: str, email: str) -> None:
        """Update technician contact information."""
        self.phone = phone
        self.email = email
        self.updated_at = datetime.now(timezone.utc)

    def update_address(self, address: Address) -> None:
        """Update technician address."""
        self.address = address
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert technician to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "company_id": str(self.company_id),
            "address": self.address.to_dict() if self.address else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
