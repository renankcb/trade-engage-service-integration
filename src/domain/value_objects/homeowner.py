"""
Homeowner value object.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Homeowner:
    """Homeowner value object."""

    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

    def __post_init__(self):
        """Validate homeowner fields."""
        if not self.name or not self.name.strip():
            raise ValueError("Homeowner name is required")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
        }
