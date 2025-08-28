"""
Technician SQLAlchemy model.
"""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import BaseModel


class TechnicianModel(BaseModel):
    """Technician database model."""

    __tablename__ = "technicians"

    name = Column(String(255), nullable=False)
    phone = Column(String(20))
    email = Column(String(255))
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # Relationships
    company = relationship("CompanyModel", back_populates="technicians")
    created_jobs = relationship("JobModel", back_populates="created_by_technician")

    def __repr__(self) -> str:
        return f"<Technician(id={self.id}, name={self.name}, company_id={self.company_id})>"
