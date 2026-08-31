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

from alembic import op

revision: str = "20260831_0003"
down_revision: str | None = "20260716_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIT_TABLES = ("matches", "players")
AUDIT_COLUMNS = ("inserted_at", "last_scraped_at", "last_updated_at")
DEPENDENT_DBT_VIEWS = ("analytics.stg_matches", "analytics.stg_players")


def _drop_dependent_dbt_views() -> None:
    # dbt-owned staging views select the audit columns, which blocks the
    # type change; they hold no data and dbt rebuilds them. IF EXISTS keeps
    # fresh databases (CI, new local setups) working.
    for view_name in DEPENDENT_DBT_VIEWS:
        op.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE")


def _convert_audit_columns(table_name: str, target_type: str) -> None:
    # One ALTER TABLE carrying all three type changes so PostgreSQL
    # rewrites the table once, not once per column; the rename is
    # metadata-only and stays separate.
    actions = ", ".join(
        f"ALTER COLUMN {column_name} TYPE {target_type}"
        f" USING {column_name} AT TIME ZONE 'UTC'"
        for column_name in AUDIT_COLUMNS
    )
    op.execute(f"ALTER TABLE {table_name} {actions}")


def upgrade() -> None:
    _drop_dependent_dbt_views()
    for table_name in AUDIT_TABLES:
        op.alter_column(
            table_name,
            "last_inserted_at",
            new_column_name="inserted_at",
        )
        _convert_audit_columns(table_name, "TIMESTAMPTZ")


def downgrade() -> None:
    _drop_dependent_dbt_views()
    for table_name in AUDIT_TABLES:
        _convert_audit_columns(table_name, "TIMESTAMP")
        op.alter_column(
            table_name,
            "inserted_at",
            new_column_name="last_inserted_at",
        )
