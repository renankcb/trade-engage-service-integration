"""add default now to updated_at company provider associations

Revision ID: 989b3b477569
Revises: c690e5a08a33
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '989b3b477569'
down_revision = 'c690e5a08a33'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Add default now() to updated_at column in company_provider_associations table
    op.execute("""
        ALTER TABLE company_provider_associations 
        ALTER COLUMN updated_at SET DEFAULT now()
    """)


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove default from updated_at column
    op.execute("""
        ALTER TABLE company_provider_associations 
        ALTER COLUMN updated_at DROP DEFAULT
    """)
