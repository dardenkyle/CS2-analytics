"""Add match_id to demo_ingestion_state and backfill it from matches.demo_links.

Demo rows are discovered inside their parent match's processing
transaction, exactly like map rows, but only `map_ingestion_state`
recorded the parent. Without a parent key the demo table cannot be
joined to its match, which the timestamp conversion in 20260923_0006
needs in order to identify which clock wrote each row (issue #213), and
which any per-match demo lookup needs in general.

The column mirrors the map table's: nullable, referencing
`matches.match_id` with ON DELETE CASCADE. Existing rows are backfilled
from `matches.demo_links`, which stores the parser's demo pairs as
`('<demo_id>', '<demo_url>')`, so each demo id maps to exactly one match.
Rows without a parent in that column stay null.

Revision ID: 20260923_0005
Revises: 20260901_0004
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_0005"
down_revision: str | None = "20260901_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Each quoted numeric token inside demo_links is a demo id; the URL in the
# same pair carries the id as its last path segment, so the id alone is
# enough to link.
BACKFILL_SQL = r"""
    UPDATE demo_ingestion_state AS d
    SET match_id = p.match_id
    FROM (
        SELECT m.match_id,
               (regexp_matches(m.demo_links, '''(\d+)''', 'g'))[1] AS demo_id
        FROM matches AS m
        WHERE m.demo_links IS NOT NULL AND m.demo_links <> ''
    ) AS p
    WHERE p.demo_id = d.demo_id AND d.match_id IS NULL
"""


def upgrade() -> None:
    op.add_column(
        "demo_ingestion_state",
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.match_id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.execute(BACKFILL_SQL)


def downgrade() -> None:
    op.drop_column("demo_ingestion_state", "match_id")
