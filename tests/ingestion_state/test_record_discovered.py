"""Tests for dated discovery recording and the backfill frontier (#121)."""

import datetime as dt
from contextlib import contextmanager

import pytest

from cs2_analytics.exceptions import MatchIngestionStateError
from cs2_analytics.ingestion_state import base_ingestion_state as base_state_module
from cs2_analytics.ingestion_state.match_ingestion_state import MatchIngestionState


class _RecordingCursor:
    """Cursor fake recording executes and serving queued fetchone results."""

    def __init__(self, fetchone_results: list[object]) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)

    def execute(self, query: str, values: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, values))

    def fetchone(self) -> object:
        return self.fetchone_results.pop(0)


class _RecordingStateDb:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor = cursor

    @contextmanager
    def get_cursor(self):
        yield self.cursor


class _FailingStateDb:
    @contextmanager
    def get_cursor(self):
        raise RuntimeError("db down")
        yield


def _state_with(monkeypatch, cursor: _RecordingCursor) -> MatchIngestionState:
    monkeypatch.setattr(
        base_state_module, "get_db", lambda: _RecordingStateDb(cursor)
    )
    return MatchIngestionState()


def test_record_discovered_upserts_dates_and_counts_new_rows(monkeypatch) -> None:
    # (xmax = 0) is True for a fresh insert, False for a conflict update.
    # COALESCE argument order is deliberate: EXCLUDED first means the
    # newest observed date wins on conflict, while a null observation
    # never erases an existing date.
    cursor = _RecordingCursor(fetchone_results=[(True,), (False,)])
    state = _state_with(monkeypatch, cursor)
    items = [
        (111, "https://example.test/matches/111", dt.date(2026, 8, 30)),
        (222, "https://example.test/matches/222", None),
    ]

    new_rows = state.record_discovered(items, source="results_scraper")

    assert new_rows == 1
    assert len(cursor.executed) == 2
    query, params = cursor.executed[0]
    assert "INSERT INTO match_ingestion_state" in query
    assert "match_date" in query
    assert "COALESCE(EXCLUDED.match_date" in query
    assert "RETURNING (xmax = 0)" in query
    assert params[:3] == (111, "https://example.test/matches/111", dt.date(2026, 8, 30))
    assert cursor.executed[1][1][:3] == (222, "https://example.test/matches/222", None)


def test_record_discovered_empty_is_a_no_op(monkeypatch) -> None:
    cursor = _RecordingCursor(fetchone_results=[])
    state = _state_with(monkeypatch, cursor)

    assert state.record_discovered([]) == 0
    assert cursor.executed == []


def test_record_discovered_wraps_database_errors(monkeypatch) -> None:
    monkeypatch.setattr(base_state_module, "get_db", lambda: _FailingStateDb())

    with pytest.raises(MatchIngestionStateError):
        MatchIngestionState().record_discovered(
            [(1, "https://example.test/matches/1", None)]
        )


def test_fetch_min_match_date_returns_frontier(monkeypatch) -> None:
    cursor = _RecordingCursor(fetchone_results=[(dt.date(2026, 5, 24),)])
    state = _state_with(monkeypatch, cursor)

    assert state.fetch_min_match_date() == dt.date(2026, 5, 24)
    query, _ = cursor.executed[0]
    assert "MIN(match_date)" in query


def test_fetch_min_match_date_none_when_nothing_dated(monkeypatch) -> None:
    cursor = _RecordingCursor(fetchone_results=[(None,)])
    state = _state_with(monkeypatch, cursor)

    assert state.fetch_min_match_date() is None


def test_fetch_min_match_date_wraps_database_errors(monkeypatch) -> None:
    monkeypatch.setattr(base_state_module, "get_db", lambda: _FailingStateDb())

    with pytest.raises(MatchIngestionStateError):
        MatchIngestionState().fetch_min_match_date()
