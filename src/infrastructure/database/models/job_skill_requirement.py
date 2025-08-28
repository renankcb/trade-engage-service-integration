"""
Job Skill Requirement SQLAlchemy model.
"""

from sqlalchemy import Column, Boolean, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import BaseModel


class JobSkillRequirementModel(BaseModel):
    """Job Skill Requirement database model."""

    __tablename__ = "job_skill_requirements"

    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    skill_name = Column(String(100), nullable=False, index=True)
    required_level = Column(String(20), nullable=False, default="intermediate", index=True)  # basic, intermediate, expert
    is_required = Column(Boolean, nullable=False, default=True)

    # Relationships
    job = relationship("JobModel", back_populates="skill_requirements")

    def __repr__(self) -> str:
        return f"<JobSkillRequirement(job_id={self.job_id}, skill={self.skill_name}, level={self.required_level})>"
