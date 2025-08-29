"""fix_jobs_timestamp_timezone_final

Revision ID: 5d055f4425ca
Revises: eace59fb355b
Create Date: 2025-01-27 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d055f4425ca"
down_revision: Union[str, Sequence[str], None] = "eace59fb355b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - fix jobs table timestamp timezone issues definitively."""

    # The error shows that created_at and updated_at are still TIMESTAMP WITHOUT TIME ZONE
    # Let's fix this definitively

    # First, let's check if the columns exist and their current type
    op.execute(
        """
        DO $$
        BEGIN
            -- Fix created_at column
            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'jobs' AND column_name = 'created_at') THEN
                ALTER TABLE jobs
                ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
                USING created_at AT TIME ZONE 'UTC';
            END IF;

            -- Fix updated_at column
            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'jobs' AND column_name = 'updated_at') THEN
                ALTER TABLE jobs
                ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
                USING updated_at AT TIME ZONE 'UTC';
            END IF;

            -- Fix completed_at column if it exists
            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'jobs' AND column_name = 'completed_at') THEN
                ALTER TABLE jobs
                ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE
                USING completed_at AT TIME ZONE 'UTC';
            END IF;
        END $$;
    """
    )

    # Also ensure all other timestamp columns in job_routings are correct
    op.execute(
        """
        DO $$
        BEGIN
            -- Fix all timestamp columns in job_routings
            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'created_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
                USING created_at AT TIME ZONE 'UTC';
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'updated_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
                USING updated_at AT TIME ZONE 'UTC';
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'next_retry_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN next_retry_at TYPE TIMESTAMP WITH TIME ZONE
                USING next_retry_at AT TIME ZONE 'UTC';
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'last_synced_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN last_synced_at TYPE TIMESTAMP WITH TIME ZONE
                USING last_synced_at AT TIME ZONE 'UTC';
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'claimed_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN claimed_at TYPE TIMESTAMP WITH TIME ZONE
                USING claimed_at AT TIME ZONE 'UTC';
            END IF;
        END $$;
    """
    )

    # Verify the fix worked by checking column types
    op.execute(
        """
        DO $$
        DECLARE
            col_type text;
        BEGIN
            -- Check jobs table
            SELECT data_type INTO col_type
            FROM information_schema.columns
            WHERE table_name = 'jobs' AND column_name = 'created_at';

            IF col_type != 'timestamp with time zone' THEN
                RAISE EXCEPTION 'created_at column type is still %', col_type;
            END IF;

            SELECT data_type INTO col_type
            FROM information_schema.columns
            WHERE table_name = 'jobs' AND column_name = 'updated_at';

            IF col_type != 'timestamp with time zone' THEN
                RAISE EXCEPTION 'updated_at column type is still %', col_type;
            END IF;
        END $$;
    """
    )


def downgrade() -> None:
    """Downgrade schema - revert timestamp timezone changes."""

    # Revert all timestamp columns back to without timezone
    # Note: This will lose timezone information

    op.execute(
        """
        DO $$
        BEGIN
            -- Revert jobs table timestamps
            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'jobs' AND column_name = 'created_at') THEN
                ALTER TABLE jobs
                ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'jobs' AND column_name = 'updated_at') THEN
                ALTER TABLE jobs
                ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'jobs' AND column_name = 'completed_at') THEN
                ALTER TABLE jobs
                ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;

            -- Revert job_routings table timestamps
            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'created_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'updated_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'next_retry_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN next_retry_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'last_synced_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN last_synced_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'job_routings' AND column_name = 'claimed_at') THEN
                ALTER TABLE job_routings
                ALTER COLUMN claimed_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;
        END $$;
    """
    )
