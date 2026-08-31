"""Add match_date to match_ingestion_state for the backfill cursor.

Discovery parses each results-section date header but previously threw it
away, so discovered-but-unprocessed rows could not be attributed to
calendar dates and no backfill progress cursor existed. A nullable
`match_date DATE` column records that date at discovery time (issue #121):
the backfill frontier is derived as `min(match_date)` over recorded rows,
and `cs2a ingest coverage` uses the same column to attribute pending
backlog to dates.

Nullable on purpose: rows discovered before this migration have no date
and pick one up on any idempotent re-sweep. No dbt object depends on the
ingestion-state tables, so no views need dropping (unlike 20260831_0003).

Revision ID: 20260901_0004
Revises: 20260831_0003
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0004"
down_revision: str | None = "20260831_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "match_ingestion_state",
        sa.Column("match_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("match_ingestion_state", "match_date")
