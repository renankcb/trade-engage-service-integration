"""
Company Skill SQLAlchemy model.
"""

from sqlalchemy import Column, Boolean, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import BaseModel


class CompanySkillModel(BaseModel):
    """Company Skill database model."""

    __tablename__ = "company_skills"

    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    skill_name = Column(String(100), nullable=False, index=True)
    skill_level = Column(String(20), nullable=False, default="intermediate", index=True)  # basic, intermediate, expert
    is_primary = Column(Boolean, nullable=False, default=False, index=True)  # Primary skill vs secondary

    # Relationships
    company = relationship("CompanyModel", back_populates="skills")

    def __repr__(self) -> str:
        return f"<CompanySkill(company_id={self.company_id}, skill={self.skill_name}, level={self.skill_level})>"
