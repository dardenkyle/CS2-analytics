"""Read-side discovery-coverage report over the matches table.

Answers "is the backfill done?" by comparing the configured discovery
window against the match dates actually present in `matches`, plus the
match_ingestion_state backlog so undiscovered gaps are distinguishable
from discovered-but-pending work. Discovered-but-unprocessed rows carry
no match date yet, so the backlog is reported as aggregate counts rather
than attributed to calendar periods.

Once a backfill cursor exists (#121), its position belongs in this
report as the completion state toward the window floor.
"""

import datetime as dt
from typing import TypedDict

from cs2_analytics.storage.db_instance import get_db

COVERAGE_PERIODS = ("day", "week")

DAYS_PER_PERIOD = {"day": 1, "week": 7}

MATCH_DATE_BOUNDS_QUERY = "SELECT MIN(date), MAX(date), COUNT(*) FROM matches;"

PERIOD_COUNTS_QUERY = """
    SELECT date_trunc(%s, date)::date, COUNT(*)
    FROM matches
    WHERE date >= %s AND date < %s
    GROUP BY 1
    ORDER BY 1;
"""

PENDING_COUNTS_QUERY = """
    SELECT status, COUNT(*)
    FROM match_ingestion_state
    WHERE status != 'processed'
    GROUP BY status
    ORDER BY status;
"""


class CoverageReport(TypedDict):
    """Discovery coverage of the target window, plus pending backlog."""

    earliest_match: dt.datetime | None
    latest_match: dt.datetime | None
    total_matches: int
    window_matches: int
    period_counts: list[tuple[dt.date, int]]
    pending_by_status: dict[str, int]


def align_period_start(day: dt.date, period: str) -> dt.date:
    """Return the period-start date containing the given day.

    Matches Postgres date_trunc semantics: days align to themselves,
    weeks to Monday, so gap detection lines up with the SQL buckets.
    """
    if period == "week":
        return day - dt.timedelta(days=day.weekday())
    return day


def compute_gap_ranges(
    window_start: dt.date,
    window_end: dt.date,
    period: str,
    period_counts: list[tuple[dt.date, int]],
) -> list[tuple[dt.date, dt.date]]:
    """Return contiguous runs of zero-match periods inside the window.

    Each range is (first_period_start, last_period_start), inclusive,
    covering consecutive periods with no counted matches.
    """
    step = dt.timedelta(days=DAYS_PER_PERIOD[period])
    counted = {period_start for period_start, count in period_counts if count > 0}
    gaps: list[tuple[dt.date, dt.date]] = []
    current = align_period_start(window_start, period)
    last_period = align_period_start(window_end, period)
    run_start: dt.date | None = None
    while current <= last_period:
        if current in counted:
            if run_start is not None:
                gaps.append((run_start, current - step))
                run_start = None
        elif run_start is None:
            run_start = current
        current = current + step
    if run_start is not None:
        gaps.append((run_start, last_period))
    return gaps


def fetch_discovery_coverage(
    window_start: dt.date, window_end: dt.date, period: str
) -> CoverageReport:
    """Return match-date coverage of the window and the pending backlog.

    The window is [window_start, window_end] inclusive; the SQL upper
    bound is exclusive at window_end + 1 day so the end date's matches
    count. `period` must be one of COVERAGE_PERIODS and is passed to
    date_trunc as a parameter.
    """
    if period not in COVERAGE_PERIODS:
        raise ValueError(
            f"period must be one of {COVERAGE_PERIODS}, got {period!r}."
        )
    upper_bound = window_end + dt.timedelta(days=1)
    with get_db().get_cursor() as cur:
        cur.execute(MATCH_DATE_BOUNDS_QUERY)
        earliest, latest, total = cur.fetchone()
        cur.execute(PERIOD_COUNTS_QUERY, (period, window_start, upper_bound))
        period_counts = [(row[0], row[1]) for row in cur.fetchall()]
        cur.execute(PENDING_COUNTS_QUERY)
        pending = dict(cur.fetchall())
    return {
        "earliest_match": earliest,
        "latest_match": latest,
        "total_matches": total,
        "window_matches": sum(count for _, count in period_counts),
        "period_counts": period_counts,
        "pending_by_status": pending,
    }
