"""alter created_at default in company_provider_associations

Revision ID: 39a4593f6696
Revises: a3f59d1a7389
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '39a4593f6696'
down_revision = 'a3f59d1a7389'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Alter created_at column to have default value now()
    op.execute("""
        ALTER TABLE company_provider_associations 
        ALTER COLUMN created_at SET DEFAULT NOW()
    """)


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove default value from created_at column
    op.execute("""
        ALTER TABLE company_provider_associations 
        ALTER COLUMN created_at DROP DEFAULT
    """)
