"""Tests for the PlayerService mart-backed read path."""

from api.services import player_service
from api.services.player_service import PlayerService


class _FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, tuple[int, ...]]] = []
        self.description = [
            ("player_id",),
            ("player_name",),
            ("maps_played",),
            ("avg_rating",),
        ]

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


def test_fetch_top_players_reads_the_aggregate_mart(monkeypatch) -> None:
    cursor = _FakeCursor([(930_000_201, "Smoke Test Player", 3, 1.25)])
    monkeypatch.setattr(player_service, "Database", lambda: _FakeDatabase(cursor))

    result = PlayerService().fetch_top_players(min_maps=2, limit=10)

    query, params = cursor.executed[0]
    assert "FROM analytics.agg_player_ratings" in query
    assert "fact_player_map_stats" not in query
    assert "GROUP BY" not in query
    assert "WHERE rated_maps >= %s" in query
    assert params == (2, 10)
    assert result[0].player_id == 930_000_201
    assert result[0].player_name == "Smoke Test Player"
    assert result[0].maps_played == 3
    assert result[0].avg_rating == 1.25


def test_fetch_top_players_orders_on_unrounded_average_with_tie_breaks(
    monkeypatch,
) -> None:
    cursor = _FakeCursor([])
    monkeypatch.setattr(player_service, "Database", lambda: _FakeDatabase(cursor))

    PlayerService().fetch_top_players(min_maps=50, limit=10)

    query, _params = cursor.executed[0]
    order_by = " ".join(query.split("ORDER BY", 1)[1].split("LIMIT", 1)[0].split())
    assert order_by == (
        "agg_player_ratings.avg_rating DESC, maps_played DESC, player_id"
    )
    assert "ROUND(avg_rating::numeric, 2) AS avg_rating" in query
    assert "avg_rating IS NOT NULL" in query


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
