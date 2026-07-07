"""Read-side summary of ingestion-state tables for status reporting."""

from cs2_analytics.storage.db_instance import get_db

INGESTION_STATE_TABLES = (
    "match_ingestion_state",
    "map_ingestion_state",
    "demo_ingestion_state",
)

STATUS_COUNTS_QUERY = "SELECT status, COUNT(*) FROM {table} GROUP BY status;"


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
