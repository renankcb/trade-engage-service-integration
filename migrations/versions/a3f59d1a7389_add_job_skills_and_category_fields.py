"""add_job_skills_and_category_fields

Revision ID: a3f59d1a7389
Revises: 6e0343f85d99
Create Date: 2025-08-27 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f59d1a7389'
down_revision: Union[str, Sequence[str], None] = '6e0343f85d99'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # 1. Add job category and skills fields to jobs table
    op.add_column('jobs', sa.Column('category', sa.String(100), nullable=True))
    op.add_column('jobs', sa.Column('required_skills', sa.JSON(), nullable=True))  # List of required skills
    op.add_column('jobs', sa.Column('skill_levels', sa.JSON(), nullable=True))    # skill_name -> required_level mapping
    
    # 2. Create index for job category only (JSON fields don't support simple indexing)
    op.create_index('idx_jobs_category', 'jobs', ['category'])


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove indexes
    op.drop_index('idx_jobs_category', table_name='jobs')
    
    # Remove columns
    op.drop_column('jobs', 'skill_levels')
    op.drop_column('jobs', 'required_skills')
    op.drop_column('jobs', 'category')
