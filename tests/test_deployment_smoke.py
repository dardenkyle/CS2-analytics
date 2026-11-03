from datetime import datetime

import pytest

from scripts import deployment_smoke


class _RecordingCursor:
    def __init__(
        self, fetchone_results: list[tuple[object, ...]] | None = None
    ) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results or [])

    def __enter__(self) -> "_RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> tuple[object, ...]:
        return self.fetchone_results.pop(0)


class _FakeDatabase:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor = cursor

    def get_cursor(self) -> _RecordingCursor:
        return self.cursor


def test_seed_smoke_source_rows_uses_repeat_safe_source_ids(monkeypatch) -> None:
    stored: dict[str, list[object]] = {}

    monkeypatch.setattr(
        deployment_smoke,
        "store_matches",
        lambda matches: stored.setdefault("matches", matches),
    )
    monkeypatch.setattr(
        deployment_smoke,
        "store_maps",
        lambda maps: stored.setdefault("maps", maps),
    )
    monkeypatch.setattr(
        deployment_smoke,
        "store_players",
        lambda players: stored.setdefault("players", players),
    )

    deployment_smoke.seed_smoke_source_rows()

    match = stored["matches"][0]
    map_obj = stored["maps"][0]
    player = stored["players"][0]

    assert match.match_id == deployment_smoke.SMOKE_MATCH_ID
    assert map_obj.map_id == deployment_smoke.SMOKE_MAP_ID
    assert map_obj.match_id == deployment_smoke.SMOKE_MATCH_ID
    assert player.map_id == deployment_smoke.SMOKE_MAP_ID
    assert player.player_id == deployment_smoke.SMOKE_PLAYER_ID
    assert player.player_name == deployment_smoke.SMOKE_PLAYER_NAME
    assert player.rating == 9.99
    assert isinstance(player.last_updated_at, datetime)


def test_cleanup_smoke_source_rows_deletes_fixed_ids_in_dependency_order(
    monkeypatch,
) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(
        deployment_smoke,
        "Database",
        lambda: _FakeDatabase(cursor),
    )

    deployment_smoke.cleanup_smoke_source_rows()

    assert cursor.executed == [
        (
            "DELETE FROM players WHERE map_id = %s AND player_id = %s;",
            (deployment_smoke.SMOKE_MAP_ID, deployment_smoke.SMOKE_PLAYER_ID),
        ),
        ("DELETE FROM maps WHERE map_id = %s;", (deployment_smoke.SMOKE_MAP_ID,)),
        (
            "DELETE FROM matches WHERE match_id = %s;",
            (deployment_smoke.SMOKE_MATCH_ID,),
        ),
    ]


def test_ensure_smoke_mart_relations_creates_schema_and_stand_in(monkeypatch) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(
        deployment_smoke,
        "Database",
        lambda: _FakeDatabase(cursor),
    )

    deployment_smoke.ensure_smoke_mart_relations()

    executed_queries = [query for query, _params in cursor.executed]
    assert executed_queries[0] == "CREATE SCHEMA IF NOT EXISTS analytics;"
    assert (
        "CREATE TABLE IF NOT EXISTS analytics.agg_player_ratings"
        in (executed_queries[1])
    )
    assert len(executed_queries) == 2


def test_seed_smoke_mart_rows_inserts_fixed_id(monkeypatch) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(
        deployment_smoke,
        "Database",
        lambda: _FakeDatabase(cursor),
    )

    deployment_smoke.seed_smoke_mart_rows()

    assert len(cursor.executed) == 1
    query, params = cursor.executed[0]
    assert "analytics.agg_player_ratings" in query
    assert params == (
        deployment_smoke.SMOKE_PLAYER_ID,
        deployment_smoke.SMOKE_PLAYER_NAME,
        1,
        1,
        9.99,
    )


def test_cleanup_smoke_mart_rows_skips_missing_relation(monkeypatch) -> None:
    cursor = _RecordingCursor(fetchone_results=[(None,)])
    monkeypatch.setattr(
        deployment_smoke,
        "Database",
        lambda: _FakeDatabase(cursor),
    )

    deployment_smoke.cleanup_smoke_mart_rows()

    executed_queries = [query for query, _params in cursor.executed]
    assert executed_queries == ["SELECT to_regclass('analytics.agg_player_ratings');"]


def test_cleanup_smoke_mart_rows_deletes_when_relation_exists(monkeypatch) -> None:
    cursor = _RecordingCursor(fetchone_results=[("analytics.agg_player_ratings",)])
    monkeypatch.setattr(
        deployment_smoke,
        "Database",
        lambda: _FakeDatabase(cursor),
    )

    deployment_smoke.cleanup_smoke_mart_rows()

    delete_queries = [
        (query, params) for query, params in cursor.executed if "DELETE" in query
    ]
    assert delete_queries == [
        (
            "DELETE FROM analytics.agg_player_ratings WHERE player_id = %s;",
            (deployment_smoke.SMOKE_PLAYER_ID,),
        ),
    ]


def test_read_timeout_seconds_rejects_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("SMOKE_API_TIMEOUT_SECONDS", "not-an-int")

    try:
        deployment_smoke.read_timeout_seconds()
    except RuntimeError as exc:
        assert "SMOKE_API_TIMEOUT_SECONDS must be an integer." in str(exc)
    else:
        raise AssertionError("Expected invalid timeout value to fail")


def test_verify_api_health_accepts_stable_payload(monkeypatch) -> None:
    def fake_request_json(_url: str, _timeout_seconds: int) -> dict[str, str]:
        return {
            "status": "ok",
            "service": "cs2-analytics-api",
        }

    monkeypatch.setattr(
        deployment_smoke,
        "request_json",
        fake_request_json,
    )

    deployment_smoke.verify_api_health("http://app:8000", 10)


def test_verify_top_players_read_requires_seeded_smoke_player(monkeypatch) -> None:
    def fake_request_json(_url: str, _timeout_seconds: int) -> list[dict[str, object]]:
        return [
            {
                "player_id": deployment_smoke.SMOKE_PLAYER_ID,
                "player_name": deployment_smoke.SMOKE_PLAYER_NAME,
                "maps_played": 1,
                "avg_rating": 9.99,
            }
        ]

    monkeypatch.setattr(
        deployment_smoke,
        "request_json",
        fake_request_json,
    )

    deployment_smoke.verify_top_players_read("http://app:8000", 10)


def test_verify_top_players_read_rejects_payload_without_smoke_player(
    monkeypatch,
) -> None:
    def fake_request_json(_url: str, _timeout_seconds: int) -> list[dict[str, object]]:
        return [
            {
                "player_id": deployment_smoke.SMOKE_PLAYER_ID + 1,
                "player_name": deployment_smoke.SMOKE_PLAYER_NAME,
                "maps_played": 1,
                "avg_rating": 9.99,
            }
        ]

    monkeypatch.setattr(
        deployment_smoke,
        "request_json",
        fake_request_json,
    )

    with pytest.raises(RuntimeError, match="Seeded smoke player was not returned"):
        deployment_smoke.verify_top_players_read("http://app:8000", 10)
