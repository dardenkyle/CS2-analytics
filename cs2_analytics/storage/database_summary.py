"""Read-side row counts and freshness for the domain tables and the analytics schema.

Backs the domain and analytics sections of `cs2a status` (#278). Counts are
exact `COUNT(*)` scans, so they are correct immediately after a dbt build
at the cost of reading each table; the newest timestamp is read in the
same scan. Views are listed but not counted: a view count re-runs its
query, and the intermediate join view is the most expensive query in the
dbt build.

Each relation is counted in its own short transaction under a lock
timeout. A dbt build swaps a rebuilt model in with a rename that needs an
exclusive lock; a long read transaction holding every mart would make
that rename wait, and API reads would queue behind it. A count that
cannot get its lock in time reports the relation as busy instead.

Domain table names come from module constants. Analytics relation names
come from `pg_class` and are quoted with `psycopg2.sql.Identifier`, so no
user input reaches a query.
"""

import datetime as dt
from typing import TypedDict

from psycopg2 import errors, sql

from cs2_analytics.exceptions import DatabaseOperationError
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.storage.ops_snapshot import RAW_TABLES

ANALYTICS_SCHEMA = "analytics"
FACT_FRESHNESS_RELATION = "fact_player_map_stats"
FACT_FRESHNESS_COLUMN = "source_updated_at"
COUNT_LOCK_TIMEOUT = "2s"
# Suffixes dbt gives the relations it builds beside a model and swaps in.
DBT_BUILD_SUFFIXES = ("__dbt_tmp", "__dbt_backup")

MATCHES_SUMMARY_QUERY = "SELECT COUNT(*), MAX(last_updated_at), MAX(date) FROM matches;"
DOMAIN_SUMMARY_QUERY = "SELECT COUNT(*), MAX(last_updated_at) FROM {table};"

SCHEMA_EXISTS_QUERY = "SELECT 1 FROM pg_namespace WHERE nspname = %s;"
# Partitions are counted through their parent. Foreign tables are left
# out: dbt does not create them here, and counting one would query a
# remote server.
ANALYTICS_RELATIONS_QUERY = """
    SELECT c.relname, c.relkind
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = %s
      AND c.relkind IN ('r', 'p', 'm', 'v')
      AND NOT c.relispartition
    ORDER BY c.relname;
"""

# pg_class.relkind values that store rows and are counted, by display name.
STORED_RELKINDS = {"r": "table", "p": "table", "m": "materialized view"}
VIEW_RELKIND = "v"

NOTE_BUSY = "busy (lock not granted; dbt build running?)"
NOTE_DROPPED = "dropped while counting"
NOTE_DBT_BUILD = "dbt build in progress"


class DomainSummary(TypedDict):
    row_counts: dict[str, int]
    newest_match_date: dt.datetime | None
    newest_updated_at: dict[str, dt.datetime | None]


class AnalyticsRelation(TypedDict):
    name: str
    kind: str
    row_count: int | None
    note: str | None


class AnalyticsSummary(TypedDict):
    built: bool
    relations: list[AnalyticsRelation]
    fact_status: str
    fact_newest_source_updated_at: dt.datetime | None


def fetch_domain_summary() -> DomainSummary:
    """Return row counts and the newest timestamps for matches, maps, and players.

    One scan per table returns both its count and its newest timestamp.
    """
    row_counts: dict[str, int] = {}
    newest_updated_at: dict[str, dt.datetime | None] = {}
    newest_match_date: dt.datetime | None = None
    with get_db().get_cursor() as cur:
        for table in RAW_TABLES:
            if table == "matches":
                cur.execute(MATCHES_SUMMARY_QUERY)
                count, newest_updated, newest_match_date = cur.fetchone()
            else:
                cur.execute(DOMAIN_SUMMARY_QUERY.format(table=table))
                count, newest_updated = cur.fetchone()
            row_counts[table] = int(count)
            newest_updated_at[table] = newest_updated
    return {
        "row_counts": row_counts,
        "newest_match_date": newest_match_date,
        "newest_updated_at": newest_updated_at,
    }


def _summarize_relation(
    schema: str, name: str, with_freshness: bool
) -> tuple[int | None, dt.datetime | None, str | None]:
    """Count one relation, and read its freshness column when asked.

    Runs in its own transaction under the lock timeout. Returns
    (row_count, newest, note): a relation whose lock is not granted, or
    that disappears before its count, comes back with a note and no count.
    A missing freshness column raises `UndefinedColumn` for the caller.
    """
    select = (
        sql.SQL("SELECT COUNT(*), MAX({}) FROM {}.{};").format(
            sql.Identifier(FACT_FRESHNESS_COLUMN),
            sql.Identifier(schema),
            sql.Identifier(name),
        )
        if with_freshness
        else sql.SQL("SELECT COUNT(*), NULL FROM {}.{};").format(
            sql.Identifier(schema), sql.Identifier(name)
        )
    )
    try:
        with get_db().get_cursor() as cur:
            cur.execute(f"SET LOCAL lock_timeout = '{COUNT_LOCK_TIMEOUT}';")
            cur.execute(select)
            count, newest = cur.fetchone()
    except DatabaseOperationError as e:
        if isinstance(e.__cause__, errors.LockNotAvailable):
            return None, None, NOTE_BUSY
        if isinstance(e.__cause__, errors.UndefinedTable):
            return None, None, NOTE_DROPPED
        raise
    return int(count), newest, None


def fetch_analytics_summary(schema: str = ANALYTICS_SCHEMA) -> AnalyticsSummary:
    """Return every relation in the dbt schema with exact counts for stored ones.

    A schema that does not exist yet (a database before its first dbt
    build) is reported as not built rather than raising. `fact_status` is
    "ok", "not built" (no fact relation), "missing column" (a fact without
    the freshness column), or the relation's note when it could not be
    read.
    """
    with get_db().get_cursor() as cur:
        cur.execute(SCHEMA_EXISTS_QUERY, (schema,))
        if cur.fetchone() is None:
            return {
                "built": False,
                "relations": [],
                "fact_status": "not built",
                "fact_newest_source_updated_at": None,
            }
        cur.execute(ANALYTICS_RELATIONS_QUERY, (schema,))
        listed = cur.fetchall()

    relations: list[AnalyticsRelation] = []
    fact_status = "not built"
    fact_newest: dt.datetime | None = None
    for name, relkind in listed:
        if relkind == VIEW_RELKIND:
            relations.append(
                {"name": name, "kind": "view", "row_count": None, "note": None}
            )
            continue
        kind = STORED_RELKINDS[relkind]
        if name.endswith(DBT_BUILD_SUFFIXES):
            relations.append(
                {"name": name, "kind": kind, "row_count": None, "note": NOTE_DBT_BUILD}
            )
            continue

        if name != FACT_FRESHNESS_RELATION:
            row_count, _, note = _summarize_relation(schema, name, False)
        else:
            try:
                row_count, fact_newest, note = _summarize_relation(schema, name, True)
                fact_status = "ok" if note is None else note
            except DatabaseOperationError as e:
                if not isinstance(e.__cause__, errors.UndefinedColumn):
                    raise
                row_count, _, note = _summarize_relation(schema, name, False)
                fact_status = "missing column" if note is None else note
        relations.append(
            {"name": name, "kind": kind, "row_count": row_count, "note": note}
        )

    return {
        "built": True,
        "relations": relations,
        "fact_status": fact_status,
        "fact_newest_source_updated_at": fact_newest,
    }
