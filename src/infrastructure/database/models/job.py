"""
Job SQLAlchemy model.
"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import BaseModel


class JobModel(BaseModel):
    """Job database model."""

    __tablename__ = "jobs"

    created_by_company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    created_by_technician_id = Column(
        UUID(as_uuid=True), ForeignKey("technicians.id"), nullable=False, index=True
    )
    summary = Column(Text, nullable=False)

    # Address fields
    street = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)

    # Homeowner contact info
    homeowner_name = Column(String(255), nullable=False)
    homeowner_phone = Column(String(20))
    homeowner_email = Column(String(255))

    # Job completion fields
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(50), default="pending", index=True)

    # Job classification and skills
    required_skills = Column(JSON, nullable=True)  # List of required skills
    skill_levels = Column(JSON, nullable=True)  # skill_name -> required_level mapping

    # Relationships
    created_by_company = relationship("CompanyModel", back_populates="created_jobs")
    created_by_technician = relationship(
        "TechnicianModel", back_populates="created_jobs"
    )
    job_routings = relationship(
        "JobRoutingModel", back_populates="job", cascade="all, delete-orphan"
    )
    # New relationships for job classification and skills
    skill_requirements = relationship(
        "JobSkillRequirementModel", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, summary={self.summary[:50]}...)>"
