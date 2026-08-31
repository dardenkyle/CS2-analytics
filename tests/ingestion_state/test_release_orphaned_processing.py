"""Tests for the startup reconciliation of orphaned 'processing' rows (#141)."""

from contextlib import contextmanager

import pytest

from cs2_analytics.exceptions import MapIngestionStateError, MatchIngestionStateError
from cs2_analytics.ingestion_state import base_ingestion_state as base_state_module
from cs2_analytics.ingestion_state.map_ingestion_state import MapIngestionState
from cs2_analytics.ingestion_state.match_ingestion_state import MatchIngestionState


class _RecordingCursor:
    def __init__(self, rowcount: int = 0) -> None:
        self.execute_query: str | None = None
        self.execute_values: tuple[object, ...] | None = None
        self.rowcount = rowcount

    def execute(self, query: str, values: tuple[object, ...]) -> None:
        self.execute_query = query
        self.execute_values = values


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


def test_release_orphaned_processing_resets_only_processing_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor(rowcount=2)
    monkeypatch.setattr(base_state_module, "get_db", lambda: _RecordingStateDb(cursor))

    released = MatchIngestionState().release_orphaned_processing()

    assert released == 2
    assert cursor.execute_query is not None
    assert "UPDATE match_ingestion_state" in cursor.execute_query
    assert "SET status = 'discovered', last_updated_at = %s" in cursor.execute_query
    assert "WHERE status = 'processing'" in cursor.execute_query
    # History is preserved: nothing touches failure_count or last_error_message.
    assert "failure_count" not in cursor.execute_query
    assert "last_error_message" not in cursor.execute_query
    assert cursor.execute_values is not None and len(cursor.execute_values) == 1


def test_release_orphaned_processing_returns_zero_when_nothing_is_stuck(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor(rowcount=0)
    monkeypatch.setattr(base_state_module, "get_db", lambda: _RecordingStateDb(cursor))

    assert MapIngestionState().release_orphaned_processing() == 0
    assert cursor.execute_query is not None
    assert "UPDATE map_ingestion_state" in cursor.execute_query


def test_release_orphaned_processing_wraps_db_errors_per_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(base_state_module, "get_db", lambda: _FailingStateDb())

    with pytest.raises(MatchIngestionStateError, match="match_ingestion_state"):
        MatchIngestionState().release_orphaned_processing()
    with pytest.raises(MapIngestionStateError, match="map_ingestion_state"):
        MapIngestionState().release_orphaned_processing()
