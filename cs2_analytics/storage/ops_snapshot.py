"""Build, save, and load the local ops page snapshot (#209).

The snapshot is one JSON document describing the ingestion picture at a
point in time: lifecycle counts and activity per state table, raw-table
row totals, and every failed, dead, or partial row with its source link.
It is written to a gitignored directory so the page opens on the last
capture without touching the database, and rebuilt on demand.

Every timestamp in the snapshot is already rendered for the operator by
`format_local`, so the page never converts dates itself and matches the
CLI exactly; `captured_at_utc` is the one machine-readable instant.
"""

import datetime as dt
import json
from pathlib import Path
from typing import TypedDict

from cs2_analytics.config.config import DB_HOST, DB_NAME
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.storage.ingestion_state_summary import (
    fetch_activity_summary,
    fetch_failure_details,
    fetch_ingestion_state_counts,
)
from cs2_analytics.utils.time_format import format_local

SNAPSHOT_SCHEMA_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT_PATH = PROJECT_ROOT / "ops_snapshots" / "latest.json"

# Stages shown on the page; the demo stage is not processed yet (#209).
PAGE_STAGE_TABLES = ("match_ingestion_state", "map_ingestion_state")
RAW_TABLES = ("matches", "maps", "players")
FAILURE_STATUSES = ("failed", "dead", "partial")

ROW_COUNT_QUERY = "SELECT COUNT(*) FROM {table};"


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


class Snapshot(TypedDict):
    schema_version: int
    captured_at: str
    captured_at_utc: str
    database: dict[str, str]
    stages: dict[str, StageSnapshot]
    totals: dict[str, int]
    failures: list[FailureSnapshot]


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


def build_snapshot() -> Snapshot:
    """Query the database once and return the full page snapshot."""
    captured = dt.datetime.now(dt.UTC)
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
        "failures": failures,
    }


def save_snapshot(snapshot: Snapshot, path: Path = DEFAULT_SNAPSHOT_PATH) -> Path:
    """Write the snapshot as JSON, creating the directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return path


def load_snapshot(path: Path = DEFAULT_SNAPSHOT_PATH) -> Snapshot | None:
    """Return the saved snapshot, or None when no capture exists yet."""
    if not path.is_file():
        return None
    loaded: Snapshot = json.loads(path.read_text(encoding="utf-8"))
    return loaded
