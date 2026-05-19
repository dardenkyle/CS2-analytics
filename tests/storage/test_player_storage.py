from datetime import UTC, datetime

import pytest

from cs2_analytics.models.player import Player
from cs2_analytics.storage import player_storage as player_storage_module


class _RecordingCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, dict[str, object]]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: dict[str, object]) -> None:
        self.executed.append((query, params))


class _FakeDb:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor = cursor

    def get_cursor(self) -> _RecordingCursor:
        return self.cursor


def _player() -> Player:
    now = datetime.now(UTC)
    return Player(
        map_id=100,
        player_id=200,
        player_name="Player",
        player_url="https://www.hltv.org/player/200/player",
        map_name="Train",
        team_name="Team",
        kills=20,
        headshots=12,
        assists=5,
        flash_assists=1,
        deaths=13,
        traded_deaths=2,
        opening_kills=4,
        opening_deaths=3,
        multi_kills=6,
        clutches_won=1,
        kast=75.0,
        kd_diff=7,
        adr=90.5,
        fk_diff=1,
        round_swing=0.07,
        rating=1.31,
        last_inserted_at=now,
        last_scraped_at=now,
        last_updated_at=now,
        data_complete=True,
    )


def _conflict_update_clause(query: str) -> str:
    assert "ON CONFLICT" in query, "Expected storage query to define an upsert conflict clause."
    return query.split("ON CONFLICT", maxsplit=1)[1]


def test_store_players_refreshes_context_and_metrics_on_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(player_storage_module, "db", _FakeDb(cursor))

    player_storage_module.store_players([_player()])

    query, params = cursor.executed[0]
    conflict_update = _conflict_update_clause(query)

    assert "ON CONFLICT (map_id, player_id)" in query
    for field_name in (
        "player_name",
        "player_url",
        "map_name",
        "team_name",
        "kills",
        "headshots",
        "assists",
        "flash_assists",
        "deaths",
        "traded_deaths",
        "opening_kills",
        "opening_deaths",
        "multi_kills",
        "clutches_won",
        "kast",
        "kd_diff",
        "adr",
        "fk_diff",
        "round_swing",
        "rating",
        "last_scraped_at",
        "last_updated_at",
        "data_complete",
    ):
        assert f"{field_name} = EXCLUDED.{field_name}" in conflict_update

    assert "last_inserted_at = EXCLUDED.last_inserted_at" not in conflict_update
    assert params["map_id"] == 100
    assert params["player_id"] == 200
