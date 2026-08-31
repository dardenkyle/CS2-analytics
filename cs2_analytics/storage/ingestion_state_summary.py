"""Read-side summaries of ingestion-state tables for status reporting.

All table and column names formatted into queries come from module
constants, never from user input, so the formatting is safe; runtime
values (status, limit) are always parametrized.
"""

import datetime as dt

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
