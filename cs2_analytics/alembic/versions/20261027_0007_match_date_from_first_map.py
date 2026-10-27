"""Set each match's date to the UTC start of its first map.

`matches.date` was written by `MatchParser._extract_match_date`, which
converted the source's unix timestamp in the writing machine's local
zone and kept only the calendar date (issue #214). Two clocks wrote
production: the desktop in America/Chicago and Docker containers in
UTC, so a match that started late in the Central evening landed on one
day or the next depending on which machine processed it, and every row
sits at midnight. `MapParser._extract_map_date` has always converted in
UTC and kept the time. The source stamps every map of a match with the
match's own start instant, the same value the match page carries, so a
match's earliest map date is exactly the instant the fixed parser would
have stored, and a later reprocess of the match writes the same value.

This migration copies `MIN(maps.date)` onto `matches.date` for every
match that has at least one map, touching only rows whose value differs,
and stamps `last_updated_at` on those rows so the incremental
`fact_player_map_stats` mart picks the corrected dates up on its next
build instead of needing a full refresh. Maps stored at exactly midnight
are ignored: the map parser's text fallback yields a date with no time
when the page has no timestamp, and that value is not the match
instant. Matches with no usable map (forfeits, series whose maps were
never processed, or whose every map was fallback-parsed) keep their
midnight date, which is the documented residual. The parser change that
ships with this migration writes the UTC instant for every new row.

Downgrade truncates `matches.date` back to midnight so the column renders
as the old parser wrote it. A row whose calendar day moved on upgrade
stays on the corrected day: the original value is not derivable, so a
true reversal needs the recovery point taken before applying.

Revision ID: 20261027_0007
Revises: 20260923_0006
Create Date: 2026-10-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261027_0007"
down_revision: str | None = "20260923_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
UPDATE matches
SET date = first_map.map_start,
    last_updated_at = now()
FROM (
    SELECT match_id, MIN(date) AS map_start
    FROM maps
    WHERE date <> date_trunc('day', date)
    GROUP BY match_id
) AS first_map
WHERE first_map.match_id = matches.match_id
  AND matches.date <> first_map.map_start;
"""

DOWNGRADE_SQL = """
UPDATE matches
SET date = date_trunc('day', date)
WHERE date <> date_trunc('day', date);
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
