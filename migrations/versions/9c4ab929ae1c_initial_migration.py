"""Initial migration

Revision ID: 9c4ab929ae1c
Revises: 
Create Date: 2025-08-27 12:13:37.364147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4ab929ae1c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    
    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sync_status_enum AS ENUM ('pending', 'synced', 'failed', 'completed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE provider_type_enum AS ENUM ('servicetitan', 'housecallpro', 'mock');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('provider_type', sa.Enum('servicetitan', 'housecallpro', 'mock', name='provider_type_enum'), nullable=False),
        sa.Column('provider_config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create technicians table
    op.create_table(
        'technicians',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('revenue', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_company_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['created_by_company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create job_routings table
    op.create_table(
        'job_routings',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('company_id_received', sa.UUID(), nullable=False),
        sa.Column('routing_reason', sa.String(length=500), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('total_sync_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['company_id_received'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_companies_provider_type', 'companies', ['provider_type'])
    op.create_index('ix_jobs_external_id', 'jobs', ['external_id'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_job_routings_job_id', 'job_routings', ['job_id'])
    op.create_index('ix_job_routings_company_id', 'job_routings', ['company_id_received'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_table('job_routings')
    op.drop_table('jobs')
    op.drop_table('technicians')
    op.drop_table('companies')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS provider_type_enum')
    op.execute('DROP TYPE IF EXISTS sync_status_enum')
    
    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
