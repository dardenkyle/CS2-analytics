"""Convert ingestion-state timestamps to TIMESTAMPTZ by their writer's clock.

The six audit columns on `match_ingestion_state`, `map_ingestion_state`,
and `demo_ingestion_state` were timezone-naive TIMESTAMP populated from
the writing process's local clock (issue #213). Two clocks wrote them:
the desktop shell in America/Chicago, and Docker containers (the compose
pipeline service and the manual GitHub Actions worker) in UTC. A uniform
reinterpretation would therefore be wrong for one of the two, so this
migration decides per value which clock wrote it and converts with that
zone. After it, the writers stamp rows with the database's `now()`, so
no client clock is involved again.

Witnesses. The parsers stamp `matches.last_scraped_at` and
`maps.last_scraped_at` as aware UTC in the same processing run that the
writer stamps `last_processed_at`, seconds apart. When the naive
`last_processed_at` agrees with that stamp to within an hour, the row was
processed by a UTC clock; a Central clock puts it five or six hours off.
Map and demo rows are discovered inside the parent match's processing
transaction, so a child's `first_seen_at` within a minute of a
UTC-processed parent's `last_processed_at` was written by that same UTC
clock; both child tables join their parent by `match_id` (demo rows
gained the column in 20260923_0005). Each witnessed instant is recorded
in a temporary anchor column.

Rule. Each column follows the witness that applies to it, never a
witness for a different event on the same row (#219): `first_seen_at`
follows the discovery witness; `last_processed_at` follows the
processing witness alone; `last_attempted_at`, `last_failed_at`, and
`last_updated_at` follow the processing witness only when they sit
within the hour of `last_processed_at`, and the discovery witness only
when they still equal the discovery stamp the writer set in the same
statement. `last_seen_at` follows the discovery witness only while it
still equals `first_seen_at`. Everything else was written from Central,
which is the majority writer and the only one since 2026-09-05. Deciding
by proximity to any UTC value on the row is not enough: a map discovered
by a container and processed from the desktop five hours later carries
two naive stamps within an hour of each other, written by different
clocks. Values with no witness (a match discovered by one run and
processed by a container in another) fall to Central, which is the
documented residual. The anchors are dropped once the conversion is done.

Downgrade restores naive TIMESTAMP rendered in America/Chicago for every
value, which is what the pre-#213 desktop writers produced; the original
mixed state is not reconstructed.

No dbt object depends on the ingestion-state tables, so no views need
dropping (unlike 20260831_0003). The `(status, priority, first_seen_at)`
indexes are rebuilt by PostgreSQL as part of the type change.

Revision ID: 20260923_0006
Revises: 20260923_0005
Create Date: 2026-09-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260923_0006"
down_revision: str | None = "20260923_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATE_COLUMNS = (
    "first_seen_at",
    "last_seen_at",
    "last_attempted_at",
    "last_processed_at",
    "last_failed_at",
    "last_updated_at",
)
STATE_TABLES = (
    "match_ingestion_state",
    "map_ingestion_state",
    "demo_ingestion_state",
)
# (state table, parser-stamped source table, shared id column) for the
# processing witness. Demo rows are never processed, so they have none.
PROCESSING_WITNESSES = (
    ("match_ingestion_state", "matches", "match_id"),
    ("map_ingestion_state", "maps", "map_id"),
)
# Child tables discovered in the parent match's transaction, joined by match_id.
CHILD_TABLES = ("map_ingestion_state", "demo_ingestion_state")
LOCAL_WRITER_ZONE = "America/Chicago"
PROCESSING_ANCHOR = "utc_processing_anchor"
DISCOVERY_ANCHOR = "utc_discovery_anchor"
# Parser and writer stamps for one run are seconds apart; the smallest
# timezone offset that could separate two clocks is an hour.
WITNESS_TOLERANCE = "INTERVAL '1 hour'"
# Child discovery rows are written in the parent's transaction, so their
# stamps sit within seconds of the parent's processing stamp.
SAME_TRANSACTION_TOLERANCE = "INTERVAL '60 seconds'"


def _add_anchor_columns() -> None:
    for table_name in STATE_TABLES:
        op.execute(
            f"ALTER TABLE {table_name}"
            f" ADD COLUMN {PROCESSING_ANCHOR} TIMESTAMP,"
            f" ADD COLUMN {DISCOVERY_ANCHOR} TIMESTAMP"
        )


def _drop_anchor_columns() -> None:
    for table_name in STATE_TABLES:
        op.execute(
            f"ALTER TABLE {table_name}"
            f" DROP COLUMN {PROCESSING_ANCHOR},"
            f" DROP COLUMN {DISCOVERY_ANCHOR}"
        )


def _mark_processing_witnesses() -> None:
    """Anchor rows whose naive processing stamp equals the parser's UTC stamp."""
    for state_table, source_table, id_column in PROCESSING_WITNESSES:
        op.execute(
            f"""
            UPDATE {state_table} AS s
            SET {PROCESSING_ANCHOR} = s.last_processed_at
            FROM {source_table} AS src
            WHERE src.{id_column} = s.{id_column}
              AND s.last_processed_at IS NOT NULL
              AND src.last_scraped_at IS NOT NULL
              AND s.last_processed_at BETWEEN
                    (src.last_scraped_at AT TIME ZONE 'UTC') - {WITNESS_TOLERANCE}
                AND (src.last_scraped_at AT TIME ZONE 'UTC') + {WITNESS_TOLERANCE}
            """
        )


def _mark_discovery_witnesses() -> None:
    """Anchor child rows discovered inside a UTC-processed parent's transaction.

    Both child tables join the parent by match_id, so a row is anchored
    only against its own parent's processing stamp.
    """
    for child_table in CHILD_TABLES:
        op.execute(
            f"""
            UPDATE {child_table} AS c
            SET {DISCOVERY_ANCHOR} = c.first_seen_at
            FROM match_ingestion_state AS p
            WHERE p.match_id = c.match_id
              AND p.{PROCESSING_ANCHOR} IS NOT NULL
              AND c.first_seen_at BETWEEN
                    p.{PROCESSING_ANCHOR} - {SAME_TRANSACTION_TOLERANCE}
                AND p.{PROCESSING_ANCHOR} + {SAME_TRANSACTION_TOLERANCE}
            """
        )


def _mark_same_run_match_discovery() -> None:
    """Anchor a match's discovery when the same container run discovered it.

    Match rows have no parent to witness discovery. A container's
    `ingest discover && process` run discovers a batch and processes it
    minutes later, so a discovery stamp within the hour before a
    UTC-witnessed processing stamp came from that run's clock.
    """
    op.execute(
        f"""
        UPDATE match_ingestion_state
        SET {DISCOVERY_ANCHOR} = first_seen_at
        WHERE {PROCESSING_ANCHOR} IS NOT NULL
          AND first_seen_at BETWEEN
                {PROCESSING_ANCHOR} - {WITNESS_TOLERANCE} AND {PROCESSING_ANCHOR}
        """
    )


def _near(column_name: str, anchor: str) -> str:
    # NULL anchor makes BETWEEN NULL, which the CASE treats as false.
    return (
        f"{column_name} BETWEEN {anchor} - {WITNESS_TOLERANCE}"
        f" AND {anchor} + {WITNESS_TOLERANCE}"
    )


# Per column: the condition under which the value was written by a UTC
# clock. Anything else converts as the local writer zone.
_DISCOVERED_UTC = f"{DISCOVERY_ANCHOR} IS NOT NULL"
_STILL_DISCOVERY_STAMP = f"last_seen_at = first_seen_at AND {_DISCOVERED_UTC}"
UTC_CONDITIONS = {
    "first_seen_at": _DISCOVERED_UTC,
    "last_seen_at": _STILL_DISCOVERY_STAMP,
    "last_processed_at": f"{PROCESSING_ANCHOR} IS NOT NULL",
    "last_attempted_at": _near("last_attempted_at", PROCESSING_ANCHOR),
    "last_failed_at": _near("last_failed_at", PROCESSING_ANCHOR),
    "last_updated_at": (
        f"({_near('last_updated_at', PROCESSING_ANCHOR)})"
        f" OR (last_updated_at = last_seen_at AND {_STILL_DISCOVERY_STAMP})"
    ),
}


def _upgrade_expression(column_name: str) -> str:
    return (
        f"CASE WHEN {UTC_CONDITIONS[column_name]}"
        f" THEN {column_name} AT TIME ZONE 'UTC'"
        f" ELSE {column_name} AT TIME ZONE '{LOCAL_WRITER_ZONE}' END"
    )


def _downgrade_expression(column_name: str) -> str:
    return f"{column_name} AT TIME ZONE '{LOCAL_WRITER_ZONE}'"


def _convert_columns(table_name: str, target_type: str, expression) -> None:
    # One ALTER TABLE carrying all six type changes so PostgreSQL rewrites
    # the table once, not once per column.
    actions = ", ".join(
        f"ALTER COLUMN {column_name} TYPE {target_type}"
        f" USING ({expression(column_name)})"
        for column_name in STATE_COLUMNS
    )
    op.execute(f"ALTER TABLE {table_name} {actions}")


def upgrade() -> None:
    _add_anchor_columns()
    _mark_processing_witnesses()
    _mark_discovery_witnesses()
    _mark_same_run_match_discovery()
    for table_name in STATE_TABLES:
        _convert_columns(table_name, "TIMESTAMPTZ", _upgrade_expression)
    _drop_anchor_columns()


def downgrade() -> None:
    for table_name in STATE_TABLES:
        _convert_columns(table_name, "TIMESTAMP", _downgrade_expression)
