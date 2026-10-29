"""Read-side row counts and freshness for the domain tables and the analytics schema.

Backs the domain and analytics sections of `cs2a status` (#278). Counts are
exact `COUNT(*)` scans, so they are correct immediately after a dbt build
at the cost of reading each table. Views are listed but not counted: a
view count re-runs its query, and the intermediate join view is the most
expensive query in the dbt build.

Domain table names come from module constants. Analytics relation names
come from `pg_class` and are quoted with `psycopg2.sql.Identifier`, so no
user input reaches a query.
"""

import datetime as dt
from typing import TypedDict

from psycopg2 import sql

from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.storage.ops_snapshot import RAW_TABLES, fetch_ingested_totals

ANALYTICS_SCHEMA = "analytics"
FACT_FRESHNESS_RELATION = "fact_player_map_stats"

NEWEST_MATCH_DATE_QUERY = "SELECT MAX(date) FROM matches;"
NEWEST_UPDATE_QUERY = "SELECT MAX(last_updated_at) FROM {table};"

SCHEMA_EXISTS_QUERY = "SELECT 1 FROM pg_namespace WHERE nspname = %s;"
ANALYTICS_RELATIONS_QUERY = """
    SELECT c.relname, c.relkind
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'm', 'v')
    ORDER BY c.relname;
"""

# pg_class.relkind values that store rows and are counted, by display name.
STORED_RELKINDS = {"r": "table", "p": "table", "m": "materialized view"}
VIEW_RELKIND = "v"


class DomainSummary(TypedDict):
    row_counts: dict[str, int]
    newest_match_date: dt.datetime | None
    newest_updated_at: dict[str, dt.datetime | None]


class AnalyticsRelation(TypedDict):
    name: str
    kind: str
    row_count: int | None


class AnalyticsSummary(TypedDict):
    built: bool
    relations: list[AnalyticsRelation]
    fact_newest_source_updated_at: dt.datetime | None


def fetch_domain_summary() -> DomainSummary:
    """Return row counts and the newest timestamps for matches, maps, and players."""
    newest_updated_at: dict[str, dt.datetime | None] = {}
    with get_db().get_cursor() as cur:
        cur.execute(NEWEST_MATCH_DATE_QUERY)
        (newest_match_date,) = cur.fetchone()
        for table in RAW_TABLES:
            cur.execute(NEWEST_UPDATE_QUERY.format(table=table))
            (newest_updated_at[table],) = cur.fetchone()
    return {
        "row_counts": fetch_ingested_totals(),
        "newest_match_date": newest_match_date,
        "newest_updated_at": newest_updated_at,
    }


def fetch_analytics_summary(schema: str = ANALYTICS_SCHEMA) -> AnalyticsSummary:
    """Return every relation in the dbt schema with exact counts for stored ones.

    A schema that does not exist yet (a database before its first dbt
    build) is reported as not built rather than raising.
    """
    with get_db().get_cursor() as cur:
        cur.execute(SCHEMA_EXISTS_QUERY, (schema,))
        if cur.fetchone() is None:
            return {
                "built": False,
                "relations": [],
                "fact_newest_source_updated_at": None,
            }

        cur.execute(ANALYTICS_RELATIONS_QUERY, (schema,))
        relations: list[AnalyticsRelation] = []
        for name, relkind in cur.fetchall():
            if relkind == VIEW_RELKIND:
                relations.append({"name": name, "kind": "view", "row_count": None})
                continue
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{};").format(
                    sql.Identifier(schema), sql.Identifier(name)
                )
            )
            (row_count,) = cur.fetchone()
            relations.append(
                {
                    "name": name,
                    "kind": STORED_RELKINDS[relkind],
                    "row_count": int(row_count),
                }
            )

        fact_newest = None
        if any(r["name"] == FACT_FRESHNESS_RELATION for r in relations):
            cur.execute(
                sql.SQL("SELECT MAX(source_updated_at) FROM {}.{};").format(
                    sql.Identifier(schema), sql.Identifier(FACT_FRESHNESS_RELATION)
                )
            )
            (fact_newest,) = cur.fetchone()

    return {
        "built": True,
        "relations": relations,
        "fact_newest_source_updated_at": fact_newest,
    }
