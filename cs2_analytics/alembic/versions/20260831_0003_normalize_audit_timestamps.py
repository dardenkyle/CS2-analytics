"""Normalize audit timestamps on matches and players to TIMESTAMPTZ.

Rename `last_inserted_at` to `inserted_at` and convert `inserted_at`,
`last_scraped_at`, and `last_updated_at` on `matches` and `players` from
timezone-naive TIMESTAMP to TIMESTAMPTZ, so all three parsed-source tables
share the audit-field convention `maps` already uses (issue #132).

Existing naive values are interpreted as UTC. That is exact for rows
written by the containerized pipeline (container clock is UTC) and by the
aware-UTC map parser path; rows written by host-local runs before
containerization may carry the host's UTC offset (up to ~6h) in these
audit fields. The skew is bounded, affects audit metadata only, and there
is no per-row discriminator to correct it, so a uniform UTC
interpretation is used.

Revision ID: 20260831_0003
Revises: 20260716_0002
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0003"
down_revision: str | None = "20260716_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIT_TABLES = ("matches", "players")
AUDIT_COLUMNS = ("inserted_at", "last_scraped_at", "last_updated_at")


def upgrade() -> None:
    for table_name in AUDIT_TABLES:
        op.alter_column(
            table_name,
            "last_inserted_at",
            new_column_name="inserted_at",
        )
        for column_name in AUDIT_COLUMNS:
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.TIMESTAMP(timezone=False),
                type_=sa.TIMESTAMP(timezone=True),
                postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
            )


def downgrade() -> None:
    for table_name in AUDIT_TABLES:
        for column_name in AUDIT_COLUMNS:
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.TIMESTAMP(timezone=True),
                type_=sa.TIMESTAMP(timezone=False),
                postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
            )
        op.alter_column(
            table_name,
            "inserted_at",
            new_column_name="last_inserted_at",
        )
