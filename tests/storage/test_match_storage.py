from datetime import UTC, datetime

import pytest

from cs2_analytics.models.match import Match
from cs2_analytics.storage import match_storage as match_storage_module


class _RecordingCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, dict[str, object]]] = []

    def execute(self, query: str, params: dict[str, object]) -> None:
        self.executed.append((query, params))


class _RecordingConnection:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor_obj = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self) -> _RecordingCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class _FakeDb:
    def __init__(self, conn: _RecordingConnection) -> None:
        self.conn = conn
        self.released = False

    def get_connection(self) -> _RecordingConnection:
        return self.conn

    def release_connection(self, conn: _RecordingConnection) -> None:
        self.released = True


def _match() -> Match:
    now = datetime.now(UTC)
    return Match(
        match_id=1,
        match_url="https://www.hltv.org/matches/1/test",
        map_links=[(11, "https://www.hltv.org/stats/matches/mapstatsid/11/test")],
        demo_links=[("demo-1", "https://www.hltv.org/download/demo/demo-1/test")],
        team1="A",
        team2="B",
        score1=16,
        score2=10,
        winner="A",
        event="Event",
        match_type="bo1",
        forfeit=False,
        date="2026-01-01",
        last_inserted_at=now,
        last_scraped_at=now,
        last_updated_at=now,
        data_complete=True,
    )


def _conflict_update_clause(query: str) -> str:
    return query.split("ON CONFLICT", maxsplit=1)[1]


def test_store_matches_refreshes_trusted_fields_on_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    conn = _RecordingConnection(cursor)
    fake_db = _FakeDb(conn)
    monkeypatch.setattr(match_storage_module, "db", fake_db)

    match_storage_module.store_matches([_match()])

    query, params = cursor.executed[0]
    conflict_update = _conflict_update_clause(query)

    for field_name in (
        "match_url",
        "team1",
        "team2",
        "score1",
        "score2",
        "winner",
        "event",
        "match_type",
        "forfeit",
        "date",
        "map_links",
        "demo_links",
        "last_scraped_at",
        "last_updated_at",
        "data_complete",
    ):
        assert f"{field_name} = EXCLUDED.{field_name}" in conflict_update

    assert "last_inserted_at = EXCLUDED.last_inserted_at" not in conflict_update
    assert params["map_links"] == str(_match().map_links)
    assert params["demo_links"] == str(_match().demo_links)
    assert conn.committed is True
    assert conn.rolled_back is False
    assert fake_db.released is True

