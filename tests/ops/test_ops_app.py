"""Endpoint tests for the local ops page app (#209)."""

import datetime as dt

from fastapi.testclient import TestClient

from cs2_analytics.exceptions import DatabaseConnectionError
from cs2_analytics.ops import app as ops_app_module

SAMPLE_SNAPSHOT = {
    "schema_version": 2,
    "captured_at": "2026-09-23 03:15:00 PM CDT",
    "captured_at_utc": "2026-09-23T20:15:00+00:00",
    "database": {"name": "cs2_db", "host": "127.0.0.1"},
    "stages": {
        "match_ingestion_state": {
            "counts": {"processed": 3},
            "last_activity_at": "2026-09-23 03:00:00 PM CDT",
            "oldest_pending_first_seen_at": "-",
        },
        "map_ingestion_state": {
            "counts": {},
            "last_activity_at": "-",
            "oldest_pending_first_seen_at": "-",
        },
    },
    "totals": {"matches": 3, "maps": 0, "players": 0},
    "volume": {"monthly": [], "weekly": []},
    "coverage": [],
    "failures": [],
}
FLOOR = dt.date(2025, 10, 1)


def _client(tmp_path):
    return TestClient(
        ops_app_module.create_ops_app(tmp_path / "latest.json", lifetime_floor=FLOOR)
    )


def test_page_serves_html_with_the_update_control(tmp_path) -> None:
    response = _client(tmp_path).get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>CS2 Analytics ops</title>" in response.text
    assert 'id="refresh"' in response.text
    assert 'id="chart-monthly"' in response.text
    assert 'id="coverage"' in response.text


def test_snapshot_is_404_before_the_first_capture(tmp_path) -> None:
    response = _client(tmp_path).get("/ops/snapshot")

    assert response.status_code == 404
    assert "No snapshot" in response.json()["detail"]


def test_snapshot_from_an_older_page_version_is_treated_as_absent(tmp_path) -> None:
    stale = dict(SAMPLE_SNAPSHOT, schema_version=1)
    (tmp_path / "latest.json").write_text(__import__("json").dumps(stale))

    response = _client(tmp_path).get("/ops/snapshot")

    assert response.status_code == 404
    assert "update button" in response.json()["detail"]


def test_refresh_builds_saves_and_returns_then_snapshot_serves_it(
    tmp_path, monkeypatch
) -> None:
    calls: list[dt.date] = []

    def _build(lifetime_floor):
        calls.append(lifetime_floor)
        return SAMPLE_SNAPSHOT

    monkeypatch.setattr(ops_app_module, "build_snapshot", _build)
    client = _client(tmp_path)

    refreshed = client.post("/ops/refresh")
    served = client.get("/ops/snapshot")

    assert refreshed.status_code == 200
    assert refreshed.json() == SAMPLE_SNAPSHOT
    assert (tmp_path / "latest.json").is_file()
    assert served.status_code == 200
    assert served.json() == SAMPLE_SNAPSHOT
    # Opening the page again costs no query: only the refresh built one,
    # and it received the configured lifetime floor.
    assert calls == [FLOOR]


def test_refresh_reports_database_unavailable_as_503(tmp_path, monkeypatch) -> None:
    def _raise(lifetime_floor):
        raise DatabaseConnectionError("no pool")

    monkeypatch.setattr(ops_app_module, "build_snapshot", _raise)

    response = _client(tmp_path).post("/ops/refresh")

    assert response.status_code == 503
    assert "Database unavailable" in response.json()["detail"]
    assert not (tmp_path / "latest.json").exists()
