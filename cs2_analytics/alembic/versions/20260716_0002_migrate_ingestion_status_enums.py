"""Migrate ingestion-state status enums.

Rename `pending` to `discovered` and add `dead` and `partial` as terminal
states across all three ingestion-state tables (issue #85).

Revision ID: 20260716_0002
Revises: 20260521_0001
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0002"
down_revision: str | None = "20260521_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INGESTION_STATE_TABLES = (
    "match_ingestion_state",
    "map_ingestion_state",
    "demo_ingestion_state",
)

OLD_STATUS_CHECK = (
    "status IN ('pending', 'processing', 'processed', 'failed', 'skipped')"
)
NEW_STATUS_CHECK = (
    "status IN ('discovered', 'processing', 'processed', 'failed', "
    "'skipped', 'dead', 'partial')"
)


def upgrade() -> None:
    for table_name in INGESTION_STATE_TABLES:
        # Drop the old constraint before rewriting rows: the old value set
        # does not include 'discovered', so the UPDATE must run unconstrained.
        op.drop_constraint(f"{table_name}_status_check", table_name, type_="check")
        op.execute(
            f"UPDATE {table_name} SET status = 'discovered' "
            "WHERE status = 'pending'"
        )
        op.create_check_constraint(
            f"{table_name}_status_check", table_name, NEW_STATUS_CHECK
        )
        op.alter_column(
            table_name,
            "status",
            existing_type=sa.Text(),
            existing_nullable=False,
            server_default=sa.text("'discovered'"),
        )


def downgrade() -> None:
    for table_name in INGESTION_STATE_TABLES:
        op.drop_constraint(f"{table_name}_status_check", table_name, type_="check")
        op.execute(
            f"UPDATE {table_name} SET status = 'failed' "
            "WHERE status IN ('dead', 'partial')"
        )
        op.execute(
            f"UPDATE {table_name} SET status = 'pending' "
            "WHERE status = 'discovered'"
        )
        op.create_check_constraint(
            f"{table_name}_status_check", table_name, OLD_STATUS_CHECK
        )
        op.alter_column(
            table_name,
            "status",
            existing_type=sa.Text(),
            existing_nullable=False,
            server_default=sa.text("'pending'"),
        )
