"""Tests for the ops page snapshot builder and its queries (#209)."""

import datetime as dt
import json

import pytest

from cs2_analytics.storage import ingestion_state_summary as summary_module
from cs2_analytics.storage import ops_snapshot as snapshot_module


def _fixed_now(monkeypatch) -> None:
    class _Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            # 10:15 PM Central on the 23rd, already the 24th in UTC.
            return dt.datetime(2026, 9, 24, 3, 15, 0, tzinfo=dt.UTC)

    monkeypatch.setattr(snapshot_module.dt, "datetime", _Clock)


def test_build_snapshot_renders_timestamps_and_shapes_sections(monkeypatch) -> None:
    _fixed_now(monkeypatch)
    monkeypatch.setattr(snapshot_module, "DB_NAME", "cs2_db")
    monkeypatch.setattr(snapshot_module, "DB_HOST", "127.0.0.1")
    monkeypatch.setattr(
        snapshot_module,
        "fetch_ingestion_state_counts",
        lambda: {
            "match_ingestion_state": {"processed": 5, "discovered": 2},
            "map_ingestion_state": {"failed": 1},
            "demo_ingestion_state": {"discovered": 9},
        },
    )
    monkeypatch.setattr(
        snapshot_module,
        "fetch_activity_summary",
        lambda: {
            "match_ingestion_state": {
                "last_activity_at": dt.datetime(2026, 9, 23, 16, 32, 59, tzinfo=dt.UTC),
                "oldest_pending_first_seen_at": dt.datetime(
                    2026, 9, 1, 13, 0, tzinfo=dt.UTC
                ),
            },
            "map_ingestion_state": {
                "last_activity_at": None,
                "oldest_pending_first_seen_at": None,
            },
            "demo_ingestion_state": {
                "last_activity_at": None,
                "oldest_pending_first_seen_at": None,
            },
        },
    )
    monkeypatch.setattr(
        snapshot_module,
        "fetch_failure_details",
        lambda statuses: [
            {
                "stage": "map",
                "id": 238491,
                "url": "https://example.test/map/238491",
                "match_id": 2398000,
                "status": "failed",
                "failure_count": 1,
                "last_failed_at": dt.datetime(2026, 9, 22, 21, 38, 41, tzinfo=dt.UTC),
                "last_error_message": "Failed to parse KAST value: '-'",
            }
        ],
    )
    monkeypatch.setattr(
        snapshot_module,
        "fetch_ingested_totals",
        lambda: {"matches": 12949, "maps": 27178, "players": 300},
    )
    monkeypatch.setattr(
        snapshot_module,
        "fetch_ingested_volume",
        lambda: {"monthly": [{"period": "2026-09-01", "matches": 1, "maps": 2}], "weekly": []},
    )
    coverage_calls: list[tuple[dt.date, dt.date]] = []

    def _windows(lifetime_floor, today):
        coverage_calls.append((lifetime_floor, today))
        return [{"label": "Lifetime from 2025-10-01"}]

    monkeypatch.setattr(snapshot_module, "build_coverage_windows", _windows)

    snapshot = snapshot_module.build_snapshot(dt.date(2025, 10, 1))

    assert snapshot["schema_version"] == 2
    assert snapshot["volume"]["monthly"][0]["maps"] == 2
    assert snapshot["coverage"] == [{"label": "Lifetime from 2025-10-01"}]
    # Coverage windows end on the operator's local date, as the CLI does,
    # not on the UTC date of the capture.
    assert coverage_calls == [(dt.date(2025, 10, 1), dt.date(2026, 9, 23))]
    assert snapshot["captured_at"] == "2026-09-23 10:15:00 PM CDT"
    assert snapshot["captured_at_utc"] == "2026-09-24T03:15:00+00:00"
    assert snapshot["database"] == {"name": "cs2_db", "host": "127.0.0.1"}
    # Demo stage is not on the page; counts are sorted by status.
    assert list(snapshot["stages"]) == ["match_ingestion_state", "map_ingestion_state"]
    assert snapshot["stages"]["match_ingestion_state"]["counts"] == {
        "discovered": 2,
        "processed": 5,
    }
    assert (
        snapshot["stages"]["match_ingestion_state"]["last_activity_at"]
        == "2026-09-23 11:32:59 AM CDT"
    )
    assert snapshot["stages"]["map_ingestion_state"]["last_activity_at"] == "-"
    assert snapshot["totals"]["matches"] == 12949
    failure = snapshot["failures"][0]
    assert failure["last_failed_at"] == "2026-09-22 04:38:41 PM CDT"
    assert failure["url"] == "https://example.test/map/238491"
    assert failure["match_id"] == 2398000
    json.dumps(snapshot)  # everything is JSON-serialisable


def test_months_back_clamps_to_month_end() -> None:
    assert snapshot_module._months_back(dt.date(2026, 3, 31), 1) == dt.date(2026, 2, 28)
    assert snapshot_module._months_back(dt.date(2026, 1, 15), 6) == dt.date(2025, 7, 15)
    assert snapshot_module._months_back(dt.date(2026, 9, 23), 12) == dt.date(2025, 9, 23)


def test_fill_series_zero_fills_missing_periods_across_both_series() -> None:
    counts = {
        "matches": {dt.date(2026, 6, 1): 4, dt.date(2026, 8, 1): 1},
        "maps": {dt.date(2026, 7, 1): 9},
    }

    points = snapshot_module._fill_series(counts, snapshot_module._next_month)

    assert points == [
        {"period": "2026-06-01", "matches": 4, "maps": 0},
        {"period": "2026-07-01", "matches": 0, "maps": 9},
        {"period": "2026-08-01", "matches": 1, "maps": 0},
    ]
    assert snapshot_module._fill_series({"matches": {}, "maps": {}}, snapshot_module._next_month) == []


def _report(**overrides):
    base = {
        "earliest_match": None,
        "latest_match": None,
        "total_matches": 100,
        "window_matches": 7,
        "period_counts": [(dt.date(2026, 9, 7), 3), (dt.date(2026, 9, 14), 4)],
        "pending_by_status": {"discovered": 2},
        "frontier": dt.date(2026, 9, 7),
        "undated_pending": 0,
    }
    base.update(overrides)
    return base


def test_build_coverage_windows_mirrors_the_cli_per_window(monkeypatch) -> None:
    calls: list[tuple[dt.date, dt.date, str]] = []

    def _fetch(window_start, window_end, period):
        calls.append((window_start, window_end, period))
        return _report()

    monkeypatch.setattr(snapshot_module, "fetch_discovery_coverage", _fetch)
    today = dt.date(2026, 9, 23)

    windows = snapshot_module.build_coverage_windows(dt.date(2025, 10, 1), today)

    assert [w["label"] for w in windows] == [
        "Last 30 days",
        "Last 6 months",
        "Last 12 months",
        "Lifetime from 2025-10-01",
    ]
    assert [c[0] for c in calls] == [
        dt.date(2026, 8, 24),
        dt.date(2026, 3, 23),
        dt.date(2025, 9, 23),
        dt.date(2025, 10, 1),
    ]
    assert all(c[1] == today and c[2] == "week" for c in calls)
    thirty = windows[0]
    assert thirty["frontier"] == "2026-09-07"
    assert thirty["swept"] == "2026-09-07 .. 2026-09-23"
    assert thirty["unswept"] == "2026-08-24 .. 2026-09-06"
    assert thirty["covered_periods"] == 2
    # Weeks are contiguous Monday buckets from the aligned window start,
    # zero-filled, so the strip has one cell per week.
    assert [w["week"] for w in thirty["weeks"]] == [
        "2026-08-24", "2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21",
    ]
    assert [w["count"] for w in thirty["weeks"]] == [0, 0, 3, 4, 0]
    # Gap ranges are classified against the frontier exactly as the CLI does.
    assert thirty["gaps"] == [
        {"start": "2026-08-24", "end": "2026-08-31", "label": "unswept"},
        {"start": "2026-09-21", "end": "2026-09-21", "label": "swept, no matches"},
    ]
    assert thirty["pending_by_status"] == {"discovered": 2}


def test_build_coverage_windows_without_a_frontier(monkeypatch) -> None:
    monkeypatch.setattr(
        snapshot_module,
        "fetch_discovery_coverage",
        lambda s, e, p: _report(frontier=None, period_counts=[]),
    )

    windows = snapshot_module.build_coverage_windows(dt.date(2026, 9, 1), dt.date(2026, 9, 23))

    lifetime = windows[-1]
    assert lifetime["frontier"] is None
    assert lifetime["swept"] is None and lifetime["unswept"] is None
    assert lifetime["gaps"][0]["label"] == "unclassified"


def test_save_replaces_atomically_and_leaves_no_temp_file(tmp_path) -> None:
    path = tmp_path / "latest.json"
    snapshot_module.save_snapshot({"schema_version": 2, "failures": [1]}, path)  # type: ignore[arg-type]
    snapshot_module.save_snapshot({"schema_version": 2, "failures": []}, path)  # type: ignore[arg-type]

    assert snapshot_module.load_snapshot(path) == {"schema_version": 2, "failures": []}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["latest.json"]


def test_load_ignores_a_snapshot_from_another_schema_version(tmp_path) -> None:
    path = tmp_path / "latest.json"
    path.write_text(json.dumps({"schema_version": 1, "failures": []}))

    assert snapshot_module.load_snapshot(path) is None


def test_save_and_load_round_trip(tmp_path) -> None:
    path = tmp_path / "nested" / "latest.json"
    snapshot = {"schema_version": 2, "captured_at": "x", "failures": []}

    assert snapshot_module.load_snapshot(path) is None
    written = snapshot_module.save_snapshot(snapshot, path)  # type: ignore[arg-type]

    assert written == path
    assert snapshot_module.load_snapshot(path) == snapshot


# --- queries against the local test database ------------------------------


PARENT_MATCH_ID = 7009


@pytest.fixture()
def seeded_failures(test_database):
    """One failed match, one dead map with a parent, one processed match."""
    with test_database.get_cursor() as cur:
        cur.execute("TRUNCATE match_ingestion_state, map_ingestion_state;")
        cur.execute(
            """
            INSERT INTO matches (match_id, match_url, team1, team2, winner, date)
            VALUES (%s, %s, 'team_a', 'team_b', 'team_a', '2026-01-01')
            ON CONFLICT (match_id) DO NOTHING;
            """,
            (PARENT_MATCH_ID, f"https://example.test/m/{PARENT_MATCH_ID}"),
        )
        cur.execute(
            """
            INSERT INTO match_ingestion_state
                (match_id, match_url, status, failure_count, last_failed_at,
                 last_error_message, first_seen_at, last_updated_at)
            VALUES
                (7001, 'https://example.test/m/7001', 'failed', 2,
                 '2026-09-20 10:00:00+00', 'boom', '2026-09-19 09:00:00+00',
                 '2026-09-20 10:00:00+00'),
                (7002, 'https://example.test/m/7002', 'processed', 0, NULL, NULL,
                 '2026-09-18 09:00:00+00', '2026-09-21 12:00:00+00'),
                (7003, 'https://example.test/m/7003', 'discovered', 0, NULL, NULL,
                 '2026-09-17 08:00:00+00', '2026-09-17 08:00:00+00');
            """
        )
        cur.execute(
            """
            INSERT INTO map_ingestion_state
                (map_id, map_url, match_id, status, failure_count, last_failed_at,
                 last_error_message, first_seen_at, last_updated_at)
            VALUES
                (8001, 'https://example.test/p/8001', %s, 'dead', 3,
                 '2026-09-21 11:00:00+00', 'gone', '2026-09-19 09:30:00+00',
                 '2026-09-21 11:00:00+00');
            """,
            (PARENT_MATCH_ID,),
        )
    yield test_database
    with test_database.get_cursor() as cur:
        cur.execute("TRUNCATE match_ingestion_state, map_ingestion_state;")
        cur.execute("DELETE FROM matches WHERE match_id = %s;", (PARENT_MATCH_ID,))


def test_fetch_failure_details_merges_stages_newest_first(seeded_failures) -> None:
    rows = summary_module.fetch_failure_details(("failed", "dead", "partial"))

    assert [(r["stage"], r["id"]) for r in rows] == [("map", 8001), ("match", 7001)]
    assert rows[0]["url"] == "https://example.test/p/8001"
    assert rows[0]["failure_count"] == 3
    assert rows[0]["match_id"] == PARENT_MATCH_ID
    assert rows[1]["match_id"] is None
    assert rows[1]["last_error_message"] == "boom"
    assert rows[1]["last_failed_at"].tzinfo is not None


def test_fetch_failure_details_filters_by_status(seeded_failures) -> None:
    only_dead = summary_module.fetch_failure_details(("dead",))

    assert [r["id"] for r in only_dead] == [8001]


def test_fetch_activity_summary_reports_latest_write_and_oldest_pending(
    seeded_failures,
) -> None:
    summary = summary_module.fetch_activity_summary()

    match = summary["match_ingestion_state"]
    assert match["last_activity_at"] == dt.datetime(2026, 9, 21, 12, 0, tzinfo=dt.UTC)
    assert match["oldest_pending_first_seen_at"] == dt.datetime(
        2026, 9, 17, 8, 0, tzinfo=dt.UTC
    )
    assert summary["map_ingestion_state"]["oldest_pending_first_seen_at"] is None
    assert summary["demo_ingestion_state"]["last_activity_at"] is None


@pytest.fixture()
def seeded_volume(test_database):
    """Two matches in different months, one map, and processed state rows."""
    with test_database.get_cursor() as cur:
        cur.execute("TRUNCATE match_ingestion_state, map_ingestion_state;")
        cur.execute("DELETE FROM matches WHERE match_id = ANY(%s);", ([7101, 7102],))
        cur.execute(
            """
            INSERT INTO matches (match_id, match_url, team1, team2, winner, date)
            VALUES (7101, 'https://example.test/m/7101', 'a', 'b', 'a', '2026-06-10'),
                   (7102, 'https://example.test/m/7102', 'a', 'b', 'a', '2026-08-02');
            """
        )
        cur.execute(
            """
            INSERT INTO maps (map_id, match_id, map_url, map_order, map_name,
                              team1_score, team2_score, map_winner, date)
            VALUES (7201, 7101, 'https://example.test/p/7201', 1, 'de_test',
                    13, 7, 'a', '2026-06-10 18:00:00');
            """
        )
        cur.execute(
            """
            INSERT INTO match_ingestion_state (match_id, match_url, status, last_processed_at)
            VALUES (7101, 'https://example.test/m/7101', 'processed', '2026-09-08 12:00:00+00'),
                   (7102, 'https://example.test/m/7102', 'processed', '2026-09-22 12:00:00+00');
            INSERT INTO map_ingestion_state (map_id, map_url, match_id, status, last_processed_at)
            VALUES (7201, 'https://example.test/p/7201', 7101, 'processed', '2026-09-09 12:00:00+00');
            """
        )
    yield test_database
    with test_database.get_cursor() as cur:
        cur.execute("TRUNCATE match_ingestion_state, map_ingestion_state;")
        cur.execute("DELETE FROM matches WHERE match_id = ANY(%s);", ([7101, 7102],))


def test_fetch_ingested_volume_buckets_by_month_and_processing_week(seeded_volume) -> None:
    volume = snapshot_module.fetch_ingested_volume()

    monthly = {p["period"]: (p["matches"], p["maps"]) for p in volume["monthly"]}
    assert monthly["2026-06-01"] == (1, 1)
    assert monthly["2026-07-01"] == (0, 0)  # zero-filled between months
    assert monthly["2026-08-01"] == (1, 0)
    weekly = {p["period"]: (p["matches"], p["maps"]) for p in volume["weekly"]}
    assert weekly["2026-09-07"] == (1, 1)
    assert weekly["2026-09-14"] == (0, 0)
    assert weekly["2026-09-21"] == (1, 0)


def test_fetch_ingested_totals_counts_raw_tables(test_database) -> None:
    totals = snapshot_module.fetch_ingested_totals()

    assert set(totals) == {"matches", "maps", "players"}
    assert all(isinstance(v, int) and v >= 0 for v in totals.values())
