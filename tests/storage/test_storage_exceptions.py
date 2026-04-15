from datetime import UTC, datetime

import pytest

from cs2_analytics.exceptions import MatchStorageError
from cs2_analytics.models.match import Match
from cs2_analytics.storage import match_storage as match_storage_module


class _FailingCursor:
    def execute(self, *args, **kwargs) -> None:
        raise RuntimeError("insert failed")


class _FailingConnection:
    def __init__(self) -> None:
        self.rollback_called = False

    def cursor(self) -> _FailingCursor:
        return _FailingCursor()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        self.rollback_called = True


class _FakeDb:
    def __init__(self, conn: _FailingConnection) -> None:
        self.conn = conn
        self.released = False

    def get_connection(self) -> _FailingConnection:
        return self.conn

    def release_connection(self, conn: _FailingConnection) -> None:
        self.released = True


def test_store_matches_wraps_database_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _FailingConnection()
    fake_db = _FakeDb(conn)
    monkeypatch.setattr(match_storage_module, "db", fake_db)
    now = datetime.now(UTC)

    match = Match(
        match_id=1,
        match_url="https://www.hltv.org/matches/1/test",
        map_links=[],
        demo_links=[],
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

    with pytest.raises(MatchStorageError, match="Failed to store match records."):
        match_storage_module.store_matches([match])

    assert conn.rollback_called is True
    assert fake_db.released is True
