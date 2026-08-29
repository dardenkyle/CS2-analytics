"""Tests for the PlayerService mart-backed read path."""

from api.services import player_service
from api.services.player_service import PlayerService


class _FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, tuple[int, ...]]] = []
        self.description = [("player_name",), ("maps_played",), ("avg_rating",)]

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[int, ...]) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class _FakeDatabase:
    def __init__(self, cursor: _FakeCursor) -> None:
        self.cursor = cursor

    def get_cursor(self) -> _FakeCursor:
        return self.cursor


def test_fetch_top_players_reads_marts_grouped_by_player_id(monkeypatch) -> None:
    cursor = _FakeCursor([("Smoke Test Player", 3, 1.25)])
    monkeypatch.setattr(player_service, "Database", lambda: _FakeDatabase(cursor))

    result = PlayerService().fetch_top_players(min_maps=2, limit=10)

    query, params = cursor.executed[0]
    assert "analytics.fact_player_map_stats" in query
    assert "analytics.dim_players" in query
    assert "players" not in query.replace("dim_players", "").replace(
        "fact_player_map_stats", ""
    )
    assert "GROUP BY fact_player_map_stats.player_id" in query
    assert params == (2, 10)
    assert result[0].player_name == "Smoke Test Player"
    assert result[0].maps_played == 3
    assert result[0].avg_rating == 1.25


def test_fetch_top_players_wraps_database_errors(monkeypatch) -> None:
    class _FailingDatabase:
        def get_cursor(self) -> None:
            raise ConnectionError("connection refused")

    monkeypatch.setattr(player_service, "Database", lambda: _FailingDatabase())

    try:
        PlayerService().fetch_top_players(min_maps=1, limit=1)
    except RuntimeError as exc:
        assert "Failed to fetch top players" in str(exc)
    else:
        raise AssertionError("Expected a database failure to raise RuntimeError")
