"""
Company SQLAlchemy model.
"""

from sqlalchemy import JSON, Boolean, Column, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship

from src.domain.value_objects.provider_type import ProviderType

from . import BaseModel


class CompanyModel(BaseModel):
    """Company database model."""

    __tablename__ = "companies"

    name = Column(String(255), nullable=False)
    provider_type = Column(
        ENUM(
            ProviderType,
            name="provider_type_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ProviderType.MOCK,
        nullable=False,
    )
    provider_config = Column(JSON, default={})
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    technicians = relationship("TechnicianModel", back_populates="company")
    created_jobs = relationship("JobModel", back_populates="created_by_company")
    received_job_routings = relationship(
        "JobRoutingModel", back_populates="company_received"
    )
    # New relationships for provider association and skills
    provider_associations = relationship("CompanyProviderAssociationModel", back_populates="company", cascade="all, delete-orphan")
    skills = relationship("CompanySkillModel", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<Company(id={self.id}, name={self.name}, provider={self.provider_type})>"
        )
