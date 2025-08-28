"""add defaults to job_categories

Revision ID: fe67670b0e52
Revises: c690e5a08a33
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fe67670b0e52'
down_revision = 'c690e5a08a33'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Add default values for job_categories table
    # 1. Set default value for is_active column to true
    op.execute("ALTER TABLE job_categories ALTER COLUMN is_active SET DEFAULT true")
    
    # 2. Set default value for created_at column to now()
    op.execute("ALTER TABLE job_categories ALTER COLUMN created_at SET DEFAULT now()")


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove default values from job_categories table
    # 1. Remove default value for is_active column
    op.execute("ALTER TABLE job_categories ALTER COLUMN is_active DROP DEFAULT")
    
    # 2. Remove default value for created_at column
    op.execute("ALTER TABLE job_categories ALTER COLUMN created_at DROP DEFAULT")
