"""Build, save, and load the local ops page snapshot (#209).

The snapshot is one JSON document describing the ingestion picture at a
point in time: lifecycle counts and activity per state table, raw-table
row totals with monthly and weekly series, discovery coverage over four
windows, and every failed, dead, or partial row with its source link.
It is written to a gitignored directory so the page opens on the last
capture without touching the database, and rebuilt on demand.

Every timestamp in the snapshot is already rendered for the operator by
`format_local`, so the page never converts dates itself and matches the
CLI exactly; `captured_at_utc` is the one machine-readable instant.
"""

import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from typing import TypedDict

from cs2_analytics.config.config import DB_HOST, DB_NAME
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.storage.discovery_coverage import (
    align_period_start,
    classify_gap,
    compute_gap_ranges,
    fetch_discovery_coverage,
)
from cs2_analytics.storage.ingestion_state_summary import (
    fetch_activity_summary,
    fetch_failure_details,
    fetch_ingestion_state_counts,
)
from cs2_analytics.utils.time_format import DISPLAY_TIMEZONE, format_local

SNAPSHOT_SCHEMA_VERSION = 2
# Relative to the invocation directory, not the package: from the repo
# root that is the gitignored ops_snapshots/, and from anywhere else it
# is still a writable location (a wheel's site-packages may not be).
SNAPSHOT_DIRNAME = "ops_snapshots"
DEFAULT_SNAPSHOT_PATH = Path(SNAPSHOT_DIRNAME) / "latest.json"

# Stages shown on the page; the demo stage is not processed yet (#209).
PAGE_STAGE_TABLES = ("match_ingestion_state", "map_ingestion_state")
RAW_TABLES = ("matches", "maps", "players")
FAILURE_STATUSES = ("failed", "dead", "partial")

ROW_COUNT_QUERY = "SELECT COUNT(*) FROM {table};"

# Matches and maps per month by the source's match date.
MONTHLY_QUERY = """
    SELECT date_trunc('month', date)::date, COUNT(*)
    FROM {table}
    GROUP BY 1
    ORDER BY 1;
"""
# Rows processed per week by the database-stamped processing instant
# (#213); weeks start on Monday, truncated in UTC so buckets are stable.
WEEKLY_PROCESSED_QUERY = """
    SELECT date_trunc('week', last_processed_at AT TIME ZONE 'UTC')::date, COUNT(*)
    FROM {table}
    WHERE last_processed_at IS NOT NULL
    GROUP BY 1
    ORDER BY 1;
"""
# (series name, raw table for the monthly series, state table for the weekly)
VOLUME_SERIES = (
    ("matches", "matches", "match_ingestion_state"),
    ("maps", "maps", "map_ingestion_state"),
)

# Coverage windows, newest first; the lifetime floor comes from the caller.
COVERAGE_WINDOW_DAYS = (("Last 30 days", 30),)
COVERAGE_WINDOW_MONTHS = (("Last 6 months", 6), ("Last 12 months", 12))
COVERAGE_PERIOD = "week"


class StageSnapshot(TypedDict):
    counts: dict[str, int]
    last_activity_at: str
    oldest_pending_first_seen_at: str


class FailureSnapshot(TypedDict):
    stage: str
    id: int
    url: str
    match_id: int | None
    status: str
    failure_count: int
    last_failed_at: str
    last_error_message: str | None


class VolumePoint(TypedDict):
    period: str
    matches: int
    maps: int


class VolumeSnapshot(TypedDict):
    monthly: list[VolumePoint]
    weekly: list[VolumePoint]


class GapSnapshot(TypedDict):
    start: str
    end: str
    label: str


class WeekCount(TypedDict):
    week: str
    count: int


class CoverageWindow(TypedDict):
    label: str
    window_start: str
    window_end: str
    frontier: str | None
    swept: str | None
    unswept: str | None
    window_matches: int
    total_matches: int
    covered_periods: int
    gaps: list[GapSnapshot]
    pending_by_status: dict[str, int]
    undated_pending: int
    weeks: list[WeekCount]


class Snapshot(TypedDict):
    schema_version: int
    captured_at: str
    captured_at_utc: str
    database: dict[str, str]
    stages: dict[str, StageSnapshot]
    totals: dict[str, int]
    volume: VolumeSnapshot
    coverage: list[CoverageWindow]
    failures: list[FailureSnapshot]


def _months_back(day: dt.date, months: int) -> dt.date:
    """Return the same day-of-month `months` earlier, clamped to month end."""
    year, month = day.year, day.month - months
    while month <= 0:
        month += 12
        year -= 1
    last_day = (_next_month(dt.date(year, month, 1)) - dt.timedelta(days=1)).day
    return dt.date(year, month, min(day.day, last_day))


def _next_month(day: dt.date) -> dt.date:
    if day.month == 12:
        return dt.date(day.year + 1, 1, 1)
    return dt.date(day.year, day.month + 1, 1)


def _next_week(day: dt.date) -> dt.date:
    return day + dt.timedelta(days=7)


def _fill_series(counts: dict[str, dict[dt.date, int]], step) -> list[VolumePoint]:
    """Zip per-series period counts into contiguous points, zero-filling gaps."""
    periods = {period for series in counts.values() for period in series}
    if not periods:
        return []
    points: list[VolumePoint] = []
    current, last = min(periods), max(periods)
    while current <= last:
        points.append(
            {
                "period": current.isoformat(),
                "matches": counts["matches"].get(current, 0),
                "maps": counts["maps"].get(current, 0),
            }
        )
        current = step(current)
    return points


def fetch_ingested_volume() -> VolumeSnapshot:
    """Return monthly rows by match date and weekly processed rows per stage."""
    monthly: dict[str, dict[dt.date, int]] = {}
    weekly: dict[str, dict[dt.date, int]] = {}
    with get_db().get_cursor() as cur:
        for name, raw_table, state_table in VOLUME_SERIES:
            cur.execute(MONTHLY_QUERY.format(table=raw_table))
            monthly[name] = {row[0]: int(row[1]) for row in cur.fetchall()}
            cur.execute(WEEKLY_PROCESSED_QUERY.format(table=state_table))
            weekly[name] = {row[0]: int(row[1]) for row in cur.fetchall()}
    return {
        "monthly": _fill_series(monthly, _next_month),
        "weekly": _fill_series(weekly, _next_week),
    }


def _coverage_window(
    label: str, window_start: dt.date, window_end: dt.date
) -> CoverageWindow:
    """One coverage panel, mirroring `cs2a ingest coverage --since window_start`."""
    report = fetch_discovery_coverage(window_start, window_end, COVERAGE_PERIOD)
    frontier = report["frontier"]
    gaps = compute_gap_ranges(
        window_start, window_end, COVERAGE_PERIOD, report["period_counts"]
    )
    frontier_period = (
        align_period_start(frontier, COVERAGE_PERIOD) if frontier is not None else None
    )
    counted = dict(report["period_counts"])
    weeks: list[WeekCount] = []
    current = align_period_start(window_start, COVERAGE_PERIOD)
    last = align_period_start(window_end, COVERAGE_PERIOD)
    while current <= last:
        weeks.append({"week": current.isoformat(), "count": counted.get(current, 0)})
        current = _next_week(current)
    swept: str | None = None
    unswept: str | None = None
    if frontier is not None:
        swept = f"{frontier.isoformat()} .. {window_end.isoformat()}"
        if frontier > window_start:
            unswept_end = frontier - dt.timedelta(days=1)
            unswept = f"{window_start.isoformat()} .. {unswept_end.isoformat()}"
    return {
        "label": label,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "frontier": frontier.isoformat() if frontier is not None else None,
        "swept": swept,
        "unswept": unswept,
        "window_matches": report["window_matches"],
        "total_matches": report["total_matches"],
        "covered_periods": len(report["period_counts"]),
        "gaps": [
            {
                "start": gap_start.isoformat(),
                "end": gap_end.isoformat(),
                "label": classify_gap(gap_start, gap_end, frontier_period),
            }
            for gap_start, gap_end in gaps
        ],
        "pending_by_status": dict(report["pending_by_status"]),
        "undated_pending": report["undated_pending"],
        "weeks": weeks,
    }


def build_coverage_windows(
    lifetime_floor: dt.date, today: dt.date
) -> list[CoverageWindow]:
    """Return the four coverage panels: 30 days, 6 months, 12 months, lifetime."""
    windows: list[CoverageWindow] = []
    for label, days in COVERAGE_WINDOW_DAYS:
        windows.append(_coverage_window(label, today - dt.timedelta(days=days), today))
    for label, months in COVERAGE_WINDOW_MONTHS:
        windows.append(_coverage_window(label, _months_back(today, months), today))
    windows.append(
        _coverage_window(
            f"Lifetime from {lifetime_floor.isoformat()}", lifetime_floor, today
        )
    )
    return windows


def fetch_ingested_totals() -> dict[str, int]:
    """Return raw-table row counts for matches, maps, and players.

    Table names come from the RAW_TABLES constant, never from user input.
    """
    totals: dict[str, int] = {}
    with get_db().get_cursor() as cur:
        for table in RAW_TABLES:
            cur.execute(ROW_COUNT_QUERY.format(table=table))
            (count,) = cur.fetchone()
            totals[table] = int(count)
    return totals


def build_snapshot(lifetime_floor: dt.date) -> Snapshot:
    """Query the database once and return the full page snapshot.

    lifetime_floor bounds the lifetime coverage panel; the three shorter
    windows are relative to today in the operator's timezone, the same
    local date `cs2a ingest coverage` ends its window on, so the panels
    mirror the CLI even when the capture happens after UTC midnight.
    """
    captured = dt.datetime.now(dt.UTC)
    today = captured.astimezone(DISPLAY_TIMEZONE).date()
    counts = fetch_ingestion_state_counts()
    activity = fetch_activity_summary()
    stages: dict[str, StageSnapshot] = {}
    for table in PAGE_STAGE_TABLES:
        stages[table] = {
            "counts": dict(sorted(counts.get(table, {}).items())),
            "last_activity_at": format_local(activity[table]["last_activity_at"]),
            "oldest_pending_first_seen_at": format_local(
                activity[table]["oldest_pending_first_seen_at"]
            ),
        }
    failures: list[FailureSnapshot] = [
        {
            "stage": row["stage"],
            "id": row["id"],
            "url": row["url"],
            "match_id": row["match_id"],
            "status": row["status"],
            "failure_count": row["failure_count"],
            "last_failed_at": format_local(row["last_failed_at"]),
            "last_error_message": row["last_error_message"],
        }
        for row in fetch_failure_details(FAILURE_STATUSES)
    ]
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "captured_at": format_local(captured),
        "captured_at_utc": captured.isoformat(timespec="seconds"),
        "database": {"name": DB_NAME, "host": DB_HOST},
        "stages": stages,
        "totals": fetch_ingested_totals(),
        "volume": fetch_ingested_volume(),
        "coverage": build_coverage_windows(lifetime_floor, today),
        "failures": failures,
    }


def save_snapshot(snapshot: Snapshot, path: Path = DEFAULT_SNAPSHOT_PATH) -> Path:
    """Write the snapshot as JSON, atomically, creating the directory if needed.

    The page can be loading the file while a refresh rewrites it, so the
    JSON goes to a temporary file in the same directory and replaces the
    target in one step: readers see the previous or the complete snapshot,
    never a truncated one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return path


def load_snapshot(path: Path = DEFAULT_SNAPSHOT_PATH) -> Snapshot | None:
    """Return the saved snapshot, or None when no usable capture exists.

    A file written by an older page version (a different schema_version)
    is treated as absent, so the page asks for an update instead of
    rendering sections it cannot read.
    """
    if not path.is_file():
        return None
    loaded: Snapshot = json.loads(path.read_text(encoding="utf-8"))
    if loaded.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        return None
    return loaded
