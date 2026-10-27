"""Reconcile each processed row's discovery date with its match's UTC day.

`match_ingestion_state.match_date` was read from the results listing's
date headers, which the source renders in the browser's zone from each
entry's instant (issue #215). Discovery has run from the desktop in
America/Chicago and from containers in UTC, so the recorded day for the
same match depended on which machine discovered it, by one or two days
in both directions against the match's own date. The parser now derives
the day from each entry's instant in UTC, so every host records the
same value; this migration brings the rows discovered before that fix
onto a host-independent value.

For every processed row, `match_date` becomes the UTC calendar day of
`matches.date`, the match's start instant corrected by 20261027_0007.
Rows that are not yet processed have no match row to reconcile against
and keep what discovery recorded. The new parser records the UTC day of
the result's posting instant, which is the match's end, so a new row
can sit one day after its match's start day when the match crosses UTC
midnight; the backfill and incremental walks tolerate that through their
overlap day and slack (ADR-0019, ADR-0020).

Downgrade is a no-op: the header-derived values are not recoverable, and
nothing in the previous revision depends on them.

Revision ID: 20261027_0008
Revises: 20261027_0007
Create Date: 2026-10-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261027_0008"
down_revision: str | None = "20261027_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
UPDATE match_ingestion_state AS state
SET match_date = matches.date::date
FROM matches
WHERE matches.match_id = state.match_id
  AND state.status = 'processed'
  AND state.match_date IS DISTINCT FROM matches.date::date;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    """No-op: the header-derived discovery dates are not recoverable."""
