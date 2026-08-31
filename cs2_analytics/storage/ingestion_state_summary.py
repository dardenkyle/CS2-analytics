"""Read-side summaries of ingestion-state tables for status reporting.

All table and column names formatted into queries come from module
constants, never from user input, so the formatting is safe; runtime
values (status, limit) are always parametrized.
"""

import datetime as dt
from typing import TypedDict

from cs2_analytics.storage.db_instance import get_db

INGESTION_STATE_TABLES = (
    "match_ingestion_state",
    "map_ingestion_state",
    "demo_ingestion_state",
)

STATUS_COUNTS_QUERY = "SELECT status, COUNT(*) FROM {table} GROUP BY status;"

# Stages with failure diagnostics exposed via `cs2a failures`; demo rows
# stay out until the demo pipeline is active.
FAILURE_STAGE_TABLES = {
    "match": ("match_ingestion_state", "match_id"),
    "map": ("map_ingestion_state", "map_id"),
}

FAILURE_ROWS_QUERY = """
    SELECT {id_column}, status, failure_count, last_failed_at, last_error_message
    FROM {table}
    WHERE status = %s
    ORDER BY last_failed_at DESC NULLS LAST, {id_column}
    LIMIT %s;
"""

FAILURE_GROUPS_QUERY = """
    SELECT last_error_message, COUNT(*), MAX(last_failed_at)
    FROM {table}
    WHERE status = %s
    GROUP BY last_error_message
    ORDER BY COUNT(*) DESC, MAX(last_failed_at) DESC NULLS LAST
    LIMIT %s;
"""


def fetch_failure_rows(
    stage: str, status: str, limit: int
) -> list[tuple[int, str, int, dt.datetime | None, str | None]]:
    """Return recent rows in the given lifecycle status for one stage.

    Each row is (id, status, failure_count, last_failed_at,
    last_error_message), most recently failed first; rows that never
    recorded a failure timestamp sort last.
    """
    table, id_column = FAILURE_STAGE_TABLES[stage]
    query = FAILURE_ROWS_QUERY.format(table=table, id_column=id_column)
    with get_db().get_cursor() as cur:
        cur.execute(query, (status, limit))
        rows: list[tuple[int, str, int, dt.datetime | None, str | None]] = (
            cur.fetchall()
        )
    return rows


def fetch_failure_groups(
    stage: str, status: str, limit: int
) -> list[tuple[str | None, int, dt.datetime | None]]:
    """Return failure rows grouped by error message for one stage.

    Each group is (last_error_message, row_count, latest last_failed_at),
    largest group first, so dominant failure modes are obvious at a
    glance.
    """
    table, _ = FAILURE_STAGE_TABLES[stage]
    query = FAILURE_GROUPS_QUERY.format(table=table)
    with get_db().get_cursor() as cur:
        cur.execute(query, (status, limit))
        groups: list[tuple[str | None, int, dt.datetime | None]] = cur.fetchall()
    return groups


# Full ingestion-state rows shown by `cs2a inspect`, in display order.
MATCH_STATE_COLUMNS = (
    "match_id",
    "match_url",
    "status",
    "first_seen_at",
    "last_seen_at",
    "last_attempted_at",
    "last_processed_at",
    "last_failed_at",
    "failure_count",
    "last_error_message",
    "source",
    "priority",
    "last_updated_at",
)

MAP_STATE_COLUMNS = (
    "map_id",
    "map_url",
    "match_id",
    "map_order",
    "status",
    "first_seen_at",
    "last_seen_at",
    "last_attempted_at",
    "last_processed_at",
    "last_failed_at",
    "failure_count",
    "last_error_message",
    "source",
    "priority",
    "last_updated_at",
)


class MatchInspection(TypedDict):
    """One match's ingestion-state row plus relational presence."""

    state: dict[str, object] | None
    match_row_exists: bool
    map_rows: int
    map_states: list[tuple[int, str]]


class MapInspection(TypedDict):
    """One map's ingestion-state row plus relational presence."""

    state: dict[str, object] | None
    map_row_exists: bool
    player_rows: int


def _fetch_state_row(
    cur, table: str, id_column: str, columns: tuple[str, ...], item_id: int
) -> dict[str, object] | None:
    """Fetch one ingestion-state row as a column->value mapping."""
    cur.execute(
        f"SELECT {', '.join(columns)} FROM {table} WHERE {id_column} = %s;",
        (item_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row, strict=True))


def fetch_match_inspection(match_id: int) -> MatchInspection:
    """Return one match's full ingestion picture.

    Combines the match_ingestion_state row (None when absent) with
    relational presence: whether the matches row exists, how many maps
    rows reference it, and each referencing map's ingestion status.
    """
    with get_db().get_cursor() as cur:
        state = _fetch_state_row(
            cur, "match_ingestion_state", "match_id", MATCH_STATE_COLUMNS, match_id
        )
        cur.execute("SELECT 1 FROM matches WHERE match_id = %s;", (match_id,))
        match_row_exists = cur.fetchone() is not None
        cur.execute("SELECT COUNT(*) FROM maps WHERE match_id = %s;", (match_id,))
        map_rows = cur.fetchone()[0]
        cur.execute(
            "SELECT map_id, status FROM map_ingestion_state"
            " WHERE match_id = %s ORDER BY map_id;",
            (match_id,),
        )
        map_states = cur.fetchall()
    return {
        "state": state,
        "match_row_exists": match_row_exists,
        "map_rows": map_rows,
        "map_states": map_states,
    }


def fetch_map_inspection(map_id: int) -> MapInspection:
    """Return one map's full ingestion picture.

    Combines the map_ingestion_state row (None when absent) with
    relational presence: whether the maps row exists and how many
    player-stats rows the map has.
    """
    with get_db().get_cursor() as cur:
        state = _fetch_state_row(
            cur, "map_ingestion_state", "map_id", MAP_STATE_COLUMNS, map_id
        )
        cur.execute("SELECT 1 FROM maps WHERE map_id = %s;", (map_id,))
        map_row_exists = cur.fetchone() is not None
        cur.execute("SELECT COUNT(*) FROM players WHERE map_id = %s;", (map_id,))
        player_rows = cur.fetchone()[0]
    return {
        "state": state,
        "map_row_exists": map_row_exists,
        "player_rows": player_rows,
    }


def fetch_ingestion_state_counts() -> dict[str, dict[str, int]]:
    """Return per-table row counts grouped by lifecycle status.

    Table names come from the INGESTION_STATE_TABLES constant, never from
    user input, so formatting them into the query is safe.
    """
    counts: dict[str, dict[str, int]] = {}
    with get_db().get_cursor() as cur:
        for table in INGESTION_STATE_TABLES:
            cur.execute(STATUS_COUNTS_QUERY.format(table=table))
            counts[table] = dict(cur.fetchall())
    return counts
