from datetime import datetime

from scripts import deployment_smoke


class _RecordingCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[int, ...]]] = []

    def __enter__(self) -> "_RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[int, ...]) -> None:
        self.executed.append((query, params))


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
