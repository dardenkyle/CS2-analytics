"""Tests for the domain and analytics summaries behind `cs2a status` (#278).

These run against the local test database. The analytics tests use a
probe schema created and dropped here, so they never depend on, or
disturb, whatever a local dbt build left in `analytics`.
"""

import datetime as dt

import pytest

from cs2_analytics.storage.database_summary import (
    fetch_analytics_summary,
    fetch_domain_summary,
)

PROBE_SCHEMA = "status_probe_278"


@pytest.fixture
def probe_schema(test_database):
    """A throwaway schema holding one table, one view, and a freshness column."""
    with test_database.get_cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {PROBE_SCHEMA} CASCADE;")
        cur.execute(f"CREATE SCHEMA {PROBE_SCHEMA};")
        cur.execute(
            f"CREATE TABLE {PROBE_SCHEMA}.fact_player_map_stats "
            "(source_updated_at TIMESTAMPTZ);"
        )
        cur.execute(
            f"INSERT INTO {PROBE_SCHEMA}.fact_player_map_stats VALUES "
            "('2026-10-27 08:00:00+00'), ('2026-10-28 08:11:42+00');"
        )
        cur.execute(f"CREATE TABLE {PROBE_SCHEMA}.dim_empty (id INT);")
        cur.execute(
            f"CREATE VIEW {PROBE_SCHEMA}.stg_probe AS "
            f"SELECT * FROM {PROBE_SCHEMA}.fact_player_map_stats;"
        )
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
        "fact_newest_source_updated_at": None,
    }


def test_analytics_summary_counts_tables_and_lists_views_uncounted(
    probe_schema,
) -> None:
    summary = fetch_analytics_summary(schema=probe_schema)

    assert summary["built"] is True
    assert summary["relations"] == [
        {"name": "dim_empty", "kind": "table", "row_count": 0},
        {"name": "fact_player_map_stats", "kind": "table", "row_count": 2},
        {"name": "stg_probe", "kind": "view", "row_count": None},
    ]
    assert summary["fact_newest_source_updated_at"] == dt.datetime(
        2026, 10, 28, 8, 11, 42, tzinfo=dt.UTC
    )


def test_domain_summary_counts_raw_tables_and_reads_newest_timestamps(
    test_database,
) -> None:
    summary = fetch_domain_summary()

    assert set(summary["row_counts"]) == {"matches", "maps", "players"}
    assert all(isinstance(v, int) and v >= 0 for v in summary["row_counts"].values())
    assert set(summary["newest_updated_at"]) == {"matches", "maps", "players"}
    with test_database.get_cursor() as cur:
        cur.execute("SELECT MAX(date) FROM matches;")
        (expected_newest_match_date,) = cur.fetchone()
    assert summary["newest_match_date"] == expected_newest_match_date
