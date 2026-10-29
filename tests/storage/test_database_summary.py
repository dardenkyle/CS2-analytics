"""Tests for the domain and analytics summaries behind `cs2a status` (#278).

These run against the local test database. The analytics tests use a
probe schema created and dropped here, so they never depend on, or
disturb, whatever a local dbt build left in `analytics`.
"""

import datetime as dt

import pytest

import cs2_analytics.storage.database_summary as summary_module
from cs2_analytics.storage.database_summary import (
    NOTE_BUSY,
    NOTE_DBT_BUILD,
    NOTE_DROPPED,
    fetch_analytics_summary,
    fetch_domain_summary,
)

PROBE_SCHEMA = "status_probe_278"


def _reset_probe_schema(test_database, *statements: str) -> None:
    with test_database.get_cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {PROBE_SCHEMA} CASCADE;")
        cur.execute(f"CREATE SCHEMA {PROBE_SCHEMA};")
        for statement in statements:
            cur.execute(statement)


@pytest.fixture
def probe_schema(test_database):
    """A throwaway schema; each test fills it through `_reset_probe_schema`."""
    yield PROBE_SCHEMA
    with test_database.get_cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {PROBE_SCHEMA} CASCADE;")


def test_analytics_summary_reports_a_missing_schema_as_not_built(
    test_database,
) -> None:
    summary = fetch_analytics_summary(schema="status_probe_absent")

    assert summary == {
        "built": False,
        "relations": [],
        "fact_status": "not built",
        "fact_newest_source_updated_at": None,
    }


def test_analytics_summary_counts_stored_relations_and_lists_views_uncounted(
    test_database, probe_schema
) -> None:
    _reset_probe_schema(
        test_database,
        f"CREATE TABLE {PROBE_SCHEMA}.fact_player_map_stats "
        "(source_updated_at TIMESTAMPTZ);",
        f"INSERT INTO {PROBE_SCHEMA}.fact_player_map_stats VALUES "
        "('2026-10-27 08:00:00+00'), ('2026-10-28 08:11:42+00');",
        f"CREATE TABLE {PROBE_SCHEMA}.dim_empty (id INT);",
        f"CREATE VIEW {PROBE_SCHEMA}.stg_probe AS "
        f"SELECT * FROM {PROBE_SCHEMA}.fact_player_map_stats;",
        f"CREATE MATERIALIZED VIEW {PROBE_SCHEMA}.mv_probe AS SELECT 1 AS one;",
        f"CREATE TABLE {PROBE_SCHEMA}.fact_matches__dbt_tmp (id INT);",
    )

    summary = fetch_analytics_summary(schema=probe_schema)

    assert summary["built"] is True
    assert summary["relations"] == [
        {"name": "dim_empty", "kind": "table", "row_count": 0, "note": None},
        {
            "name": "fact_matches__dbt_tmp",
            "kind": "table",
            "row_count": None,
            "note": NOTE_DBT_BUILD,
        },
        {"name": "fact_player_map_stats", "kind": "table", "row_count": 2, "note": None},
        {"name": "mv_probe", "kind": "materialized view", "row_count": 1, "note": None},
        {"name": "stg_probe", "kind": "view", "row_count": None, "note": None},
    ]
    assert summary["fact_status"] == "ok"
    assert summary["fact_newest_source_updated_at"] == dt.datetime(
        2026, 10, 28, 8, 11, 42, tzinfo=dt.UTC
    )


def test_analytics_summary_lists_a_partitioned_table_once(
    test_database, probe_schema
) -> None:
    _reset_probe_schema(
        test_database,
        f"CREATE TABLE {PROBE_SCHEMA}.parted (id INT) PARTITION BY RANGE (id);",
        f"CREATE TABLE {PROBE_SCHEMA}.parted_low PARTITION OF {PROBE_SCHEMA}.parted "
        "FOR VALUES FROM (0) TO (10);",
        f"INSERT INTO {PROBE_SCHEMA}.parted VALUES (1), (2), (3);",
    )

    summary = fetch_analytics_summary(schema=probe_schema)

    assert summary["relations"] == [
        {"name": "parted", "kind": "table", "row_count": 3, "note": None}
    ]


def test_analytics_summary_reports_a_missing_fact_and_a_missing_column(
    test_database, probe_schema
) -> None:
    _reset_probe_schema(test_database, f"CREATE TABLE {PROBE_SCHEMA}.dim_only (id INT);")
    assert fetch_analytics_summary(schema=probe_schema)["fact_status"] == "not built"

    _reset_probe_schema(
        test_database,
        f"CREATE TABLE {PROBE_SCHEMA}.fact_player_map_stats (map_id INT);",
        f"INSERT INTO {PROBE_SCHEMA}.fact_player_map_stats VALUES (1);",
    )
    summary = fetch_analytics_summary(schema=probe_schema)

    assert summary["fact_status"] == "missing column"
    assert summary["fact_newest_source_updated_at"] is None
    assert summary["relations"] == [
        {"name": "fact_player_map_stats", "kind": "table", "row_count": 1, "note": None}
    ]


def test_analytics_summary_reports_a_locked_relation_as_busy(
    test_database, probe_schema, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reset_probe_schema(test_database, f"CREATE TABLE {PROBE_SCHEMA}.locked (id INT);")
    monkeypatch.setattr(summary_module, "COUNT_LOCK_TIMEOUT", "100ms")
    holder = test_database.get_connection()
    try:
        with holder.cursor() as cur:
            cur.execute(f"LOCK TABLE {PROBE_SCHEMA}.locked IN ACCESS EXCLUSIVE MODE;")

        summary = fetch_analytics_summary(schema=probe_schema)
    finally:
        holder.rollback()
        test_database.release_connection(holder)

    assert summary["relations"] == [
        {"name": "locked", "kind": "table", "row_count": None, "note": NOTE_BUSY}
    ]


def test_a_relation_dropped_before_its_count_is_reported_not_raised(
    test_database, probe_schema
) -> None:
    _reset_probe_schema(test_database)

    assert summary_module._summarize_relation(probe_schema, "gone", False) == (
        None,
        None,
        NOTE_DROPPED,
    )


def test_domain_summary_reads_each_table_count_and_newest_timestamp(
    test_database,
) -> None:
    summary = fetch_domain_summary()

    expected_counts: dict[str, int] = {}
    expected_newest: dict[str, dt.datetime | None] = {}
    with test_database.get_cursor() as cur:
        for table in ("matches", "maps", "players"):
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            (expected_counts[table],) = cur.fetchone()
            cur.execute(f"SELECT MAX(last_updated_at) FROM {table};")
            (expected_newest[table],) = cur.fetchone()
        cur.execute("SELECT MAX(date) FROM matches;")
        (expected_match_date,) = cur.fetchone()

    assert summary == {
        "row_counts": expected_counts,
        "newest_match_date": expected_match_date,
        "newest_updated_at": expected_newest,
    }
