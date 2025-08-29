"""fix_timestamp_timezone_issues

Revision ID: eace59fb355b
Revises: 667caac8a79b
Create Date: 2025-01-27 12:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eace59fb355b"
down_revision: Union[str, Sequence[str], None] = "667caac8a79b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - fix timestamp timezone issues."""

    # Fix timestamp columns to use timezone
    # This is needed because SQLAlchemy expects timezone-aware timestamps

    # Fix jobs table timestamps
    op.execute(
        """
        ALTER TABLE jobs
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE jobs
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
        USING updated_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE jobs
        ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE
        USING completed_at AT TIME ZONE 'UTC'
    """
    )

    # Fix job_routings table timestamps
    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
        USING updated_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN next_retry_at TYPE TIMESTAMP WITH TIME ZONE
        USING next_retry_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN last_synced_at TYPE TIMESTAMP WITH TIME ZONE
        USING last_synced_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN claimed_at TYPE TIMESTAMP WITH TIME ZONE
        USING claimed_at AT TIME ZONE 'UTC'
    """
    )

    # Fix companies table timestamps
    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
        USING updated_at AT TIME ZONE 'UTC'
    """
    )

    # Fix technicians table timestamps
    op.execute(
        """
        ALTER TABLE technicians
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE technicians
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
        USING updated_at AT TIME ZONE 'UTC'
    """
    )

    # Fix outbox_events table timestamps
    op.execute(
        """
        ALTER TABLE outbox_events
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC'
    """
    )

    op.execute(
        """
        ALTER TABLE outbox_events
        ALTER COLUMN processed_at TYPE TIMESTAMP WITH TIME ZONE
        USING processed_at AT TIME ZONE 'UTC'
    """
    )


def downgrade() -> None:
    """Downgrade schema - revert timestamp timezone changes."""

    # Revert all timestamp columns back to without timezone
    # Note: This will lose timezone information

    # Revert jobs table timestamps
    op.execute(
        """
        ALTER TABLE jobs
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE jobs
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE jobs
        ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    # Revert job_routings table timestamps
    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN next_retry_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN last_synced_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE job_routings
        ALTER COLUMN claimed_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    # Revert companies table timestamps
    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    # Revert technicians table timestamps
    op.execute(
        """
        ALTER TABLE technicians
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE technicians
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    # Revert outbox_events table timestamps
    op.execute(
        """
        ALTER TABLE outbox_events
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )

    op.execute(
        """
        ALTER TABLE outbox_events
        ALTER COLUMN processed_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """
    )
