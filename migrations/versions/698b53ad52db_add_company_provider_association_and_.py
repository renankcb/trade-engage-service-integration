"""add_company_provider_association_and_skills

Revision ID: 698b53ad52db
Revises: 1adfe0f8fab7
Create Date: 2025-08-27 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '698b53ad52db'
down_revision: Union[str, Sequence[str], None] = '1adfe0f8fab7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # 1. Create company_provider_associations table
    op.create_table(
        'company_provider_associations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('provider_config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('company_id', 'provider_type', name='uq_company_provider')
    )
    
    # 2. Create company_skills table for intelligent matching
    op.create_table(
        'company_skills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('skill_name', sa.String(100), nullable=False),
        sa.Column('skill_level', sa.String(20), nullable=False, default='intermediate'),  # basic, intermediate, expert
        sa.Column('is_primary', sa.Boolean(), nullable=False, default=False),  # Primary skill vs secondary
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('company_id', 'skill_name', name='uq_company_skill')
    )
    
    # 3. Create job_categories table for job classification
    op.create_table(
        'job_categories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_category_id', sa.UUID(), nullable=True),  # For hierarchical categories
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_category_id'], ['job_categories.id'], ondelete='SET NULL')
    )
    
    # 4. Create job_skill_requirements table for job-skill mapping
    op.create_table(
        'job_skill_requirements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('skill_name', sa.String(100), nullable=False),
        sa.Column('required_level', sa.String(20), nullable=False, default='intermediate'),
        sa.Column('is_required', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('job_id', 'skill_name', name='uq_job_skill_requirement')
    )
    
    # 5. Add indexes for performance
    op.create_index('idx_company_provider_type', 'company_provider_associations', ['provider_type'])
    op.create_index('idx_company_provider_active', 'company_provider_associations', ['is_active'])
    op.create_index('idx_company_skills_skill', 'company_skills', ['skill_name'])
    op.create_index('idx_company_skills_level', 'company_skills', ['skill_level'])
    op.create_index('idx_company_skills_primary', 'company_skills', ['is_primary'])
    op.create_index('idx_job_categories_parent', 'job_categories', ['parent_category_id'])
    op.create_index('idx_job_skill_requirements_skill', 'job_skill_requirements', ['skill_name'])
    op.create_index('idx_job_skill_requirements_level', 'job_skill_requirements', ['required_level'])


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove indexes
    op.drop_index('idx_job_skill_requirements_level', table_name='job_skill_requirements')
    op.drop_index('idx_job_skill_requirements_skill', table_name='job_skill_requirements')
    op.drop_index('idx_job_categories_parent', table_name='job_categories')
    op.drop_index('idx_company_skills_primary', table_name='company_skills')
    op.drop_index('idx_company_skills_level', table_name='company_skills')
    op.drop_index('idx_company_skills_skill', table_name='company_skills')
    op.drop_index('idx_company_provider_active', table_name='company_provider_associations')
    op.drop_index('idx_company_provider_type', table_name='company_provider_associations')
    
    # Remove tables
    op.drop_table('job_skill_requirements')
    op.drop_table('job_categories')
    op.drop_table('company_skills')
    op.drop_table('company_provider_associations')
