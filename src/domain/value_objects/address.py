"""
Address value object.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Address:
    """Address value object."""

    street: str
    city: str
    state: str
    zip_code: str

    def __post_init__(self):
        """Validate address fields."""
        if not self.street or not self.street.strip():
            raise ValueError("Street is required")
        if not self.city or not self.city.strip():
            raise ValueError("City is required")
        if not self.state or len(self.state) != 2:
            raise ValueError("State must be 2 characters")
        if not self.zip_code or not self.zip_code.strip():
            raise ValueError("ZIP code is required")

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
        }
