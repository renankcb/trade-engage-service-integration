"""
Job Matching Engine for intelligent company selection.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CompanyMatch:
    """Company match result."""
    company_id: UUID
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    provider_type: str
    is_active: bool


@dataclass
class JobRequirements:
    """Job requirements for matching."""
    job_id: UUID
    required_skills: List[str]
    skill_levels: Dict[str, str]  # skill_name -> required_level
    location: Optional[Dict[str, str]] = None  # address info
    category: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent


class JobMatchingEngine:
    """Intelligent engine for matching jobs with companies."""

    def __init__(self):
        self.logger = logger

    async def find_matching_companies(
        self,
        job_requirements: JobRequirements,
        available_companies: List[Dict[str, Any]],
        max_results: int = 10
    ) -> List[CompanyMatch]:
        """
        Find companies that match the job requirements.
        
        Args:
            job_requirements: Job requirements and constraints
            available_companies: List of available companies with their data
            max_results: Maximum number of results to return
            
        Returns:
            List of CompanyMatch objects sorted by score (highest first)
        """
        self.logger.info(
            "Finding matching companies for job",
            job_id=str(job_requirements.job_id),
            required_skills=job_requirements.required_skills,
            max_results=max_results
        )
        
        matches = []
        
        for company in available_companies:
            match_score, matched_skills, missing_skills = self._calculate_match_score(
                job_requirements, company
            )
            
            if match_score > 0:  # Only include companies with some match
                company_match = CompanyMatch(
                    company_id=company["id"],
                    score=match_score,
                    matched_skills=matched_skills,
                    missing_skills=missing_skills,
                    provider_type=company.get("provider_type", "unknown"),
                    is_active=company.get("is_active", False)
                )
                matches.append(company_match)
        
        # Sort by score (highest first) and limit results
        matches.sort(key=lambda x: x.score, reverse=True)
        matches = matches[:max_results]
        
        self.logger.info(
            "Found matching companies",
            job_id=str(job_requirements.job_id),
            total_matches=len(matches),
            top_score=matches[0].score if matches else 0
        )
        
        return matches

    def _calculate_match_score(
        self,
        job_requirements: JobRequirements,
        company: Dict[str, Any]
    ) -> tuple[float, List[str], List[str]]:
        """
        Calculate match score between job requirements and company capabilities.
        
        Returns:
            Tuple of (score, matched_skills, missing_skills)
        """
        company_skills = company.get("skills", [])
        company_skill_levels = company.get("skill_levels", {})
        
        matched_skills = []
        missing_skills = []
        total_score = 0.0
        
        # Calculate skill-based score
        for skill_name, required_level in job_requirements.skill_levels.items():
            if skill_name in company_skills:
                company_level = company_skill_levels.get(skill_name, "basic")
                skill_score = self._calculate_skill_level_score(required_level, company_level)
                total_score += skill_score
                matched_skills.append(skill_name)
                
                self.logger.debug(
                    "Skill match found",
                    skill=skill_name,
                    required_level=required_level,
                    company_level=company_level,
                    score=skill_score
                )
            else:
                missing_skills.append(skill_name)
                # Penalty for missing required skills
                if skill_name in job_requirements.required_skills:
                    total_score -= 2.0  # Higher penalty for required skills
        
        # Bonus for companies with primary skills matching job requirements
        primary_skills = [skill for skill in company_skills if company.get("is_primary_skill", {}).get(skill, False)]
        for skill in primary_skills:
            if skill in job_requirements.required_skills:
                total_score += 1.5  # Bonus for primary skills
        
        # Bonus for active companies
        if company.get("is_active", False):
            total_score += 0.5
        
        # Bonus for companies with provider configured
        if company.get("provider_type") and company.get("provider_type") != "none":
            total_score += 0.3
        
        # Location-based scoring (if implemented)
        if job_requirements.location and company.get("location"):
            location_score = self._calculate_location_score(
                job_requirements.location, company["location"]
            )
            total_score += location_score
        
        # Ensure score is not negative
        total_score = max(0.0, total_score)
        
        return total_score, matched_skills, missing_skills

    def _calculate_skill_level_score(self, required_level: str, company_level: str) -> float:
        """Calculate score based on skill level matching."""
        level_scores = {"basic": 1.0, "intermediate": 2.0, "expert": 3.0}
        
        required_score = level_scores.get(required_level, 1.0)
        company_score = level_scores.get(company_level, 0.0)
        
        if company_score >= required_score:
            # Bonus for exceeding requirements
            return company_score + (company_score - required_score) * 0.5
        else:
            # Penalty for not meeting requirements
            return company_score * 0.5

    def _calculate_location_score(self, job_location: Dict[str, str], company_location: Dict[str, str]) -> float:
        """Calculate location-based score (placeholder for future implementation)."""
        # TODO: Implement location-based scoring (distance, service area, etc.)
        # For now, return 0.0
        return 0.0

    async def get_company_skills(self, company_id: UUID) -> List[Dict[str, Any]]:
        """Get company skills for matching (to be implemented with repository)."""
        # TODO: Implement with CompanySkillRepository
        return []

    async def get_job_requirements(self, job_id: UUID) -> JobRequirements:
        """Get job requirements for matching (to be implemented with repository)."""
        # TODO: Implement with JobSkillRequirementRepository
        return JobRequirements(
            job_id=job_id,
            required_skills=[],
            skill_levels={}
        )
