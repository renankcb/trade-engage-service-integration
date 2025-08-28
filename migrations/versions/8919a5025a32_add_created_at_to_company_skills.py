"""add created_at default to company_skills

Revision ID: 8919a5025a32
Revises: a3f59d1a7389
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8919a5025a32'
down_revision = 'a3f59d1a7389'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Add default value now() to existing created_at column in company_skills table
    op.execute("ALTER TABLE company_skills ALTER COLUMN created_at SET DEFAULT now()")


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove default value from created_at column
    op.execute("ALTER TABLE company_skills ALTER COLUMN created_at DROP DEFAULT")
