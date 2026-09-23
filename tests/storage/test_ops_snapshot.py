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
            return dt.datetime(2026, 9, 23, 20, 15, 0, tzinfo=dt.UTC)

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

    snapshot = snapshot_module.build_snapshot()

    assert snapshot["schema_version"] == 1
    assert snapshot["captured_at"] == "2026-09-23 03:15:00 PM CDT"
    assert snapshot["captured_at_utc"] == "2026-09-23T20:15:00+00:00"
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


def test_save_replaces_atomically_and_leaves_no_temp_file(tmp_path) -> None:
    path = tmp_path / "latest.json"
    snapshot_module.save_snapshot({"schema_version": 1, "failures": []}, path)  # type: ignore[arg-type]
    snapshot_module.save_snapshot({"schema_version": 2, "failures": []}, path)  # type: ignore[arg-type]

    assert snapshot_module.load_snapshot(path) == {"schema_version": 2, "failures": []}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["latest.json"]


def test_save_and_load_round_trip(tmp_path) -> None:
    path = tmp_path / "nested" / "latest.json"
    snapshot = {"schema_version": 1, "captured_at": "x", "failures": []}

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


def test_fetch_ingested_totals_counts_raw_tables(test_database) -> None:
    totals = snapshot_module.fetch_ingested_totals()

    assert set(totals) == {"matches", "maps", "players"}
    assert all(isinstance(v, int) and v >= 0 for v in totals.values())
