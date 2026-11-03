"""Tests for the player routes' response handling."""

import pytest
from fastapi import Response

from api.routes import players as players_routes
from api.schemas.player import PlayerStats


class _FakePlayerService:
    def __init__(self, players: list[PlayerStats]) -> None:
        self.players = players
        self.calls: list[tuple[int, int]] = []

    def fetch_top_players(self, min_maps: int, limit: int) -> list[PlayerStats]:
        self.calls.append((min_maps, limit))
        return self.players


class _FailingPlayerService:
    def fetch_top_players(self, min_maps: int, limit: int) -> list[PlayerStats]:
        raise RuntimeError("Failed to fetch top players: connection refused")


def test_top_players_sets_a_short_public_cache_header(monkeypatch) -> None:
    player = PlayerStats(
        player_id=1, player_name="Player One", maps_played=60, avg_rating=1.21
    )
    service = _FakePlayerService([player])
    monkeypatch.setattr(players_routes, "PlayerService", lambda: service)
    response = Response()

    result = players_routes.get_top_players(response, min_maps=50, limit=10)

    assert result == [player]
    assert service.calls == [(50, 10)]
    assert response.headers["Cache-Control"] == (
        f"public, max-age={players_routes.TOP_PLAYERS_CACHE_SECONDS}"
    )


def test_top_players_failure_leaves_no_cache_header(monkeypatch) -> None:
    monkeypatch.setattr(players_routes, "PlayerService", _FailingPlayerService)
    response = Response()

    with pytest.raises(RuntimeError, match="Failed to fetch top players"):
        players_routes.get_top_players(response, min_maps=50, limit=10)

    assert "Cache-Control" not in response.headers
