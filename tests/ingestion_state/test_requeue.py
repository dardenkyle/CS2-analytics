"""Tests for the ingestion-state requeue path used by `cs2a retry` (#122).

Covers the storage-layer query building for candidate lookup and the
status reset, including the decision that failure_count is preserved as
history rather than reset on requeue.
"""

from contextlib import contextmanager

import pytest

from cs2_analytics.exceptions import MatchIngestionStateError
from cs2_analytics.ingestion_state import base_ingestion_state as base_state_module
from cs2_analytics.ingestion_state.match_ingestion_state import MatchIngestionState


class _RecordingCursor:
    def __init__(
        self,
        rows: list[tuple] | None = None,
        rowcount: int = 0,
    ) -> None:
        self.execute_query: str | None = None
        self.execute_values: tuple[object, ...] | None = None
        self.rows = rows if rows is not None else []
        self.rowcount = rowcount

    def execute(self, query: str, values: tuple[object, ...]) -> None:
        self.execute_query = query
        self.execute_values = values

    def fetchall(self) -> list[tuple]:
        return self.rows


class _RecordingStateDb:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor = cursor
        self.cursor_uses = 0

    @contextmanager
    def get_cursor(self):
        self.cursor_uses += 1
        yield self.cursor


class _FailingStateDb:
    @contextmanager
    def get_cursor(self):
        raise RuntimeError("db down")
        yield


def test_fetch_requeue_candidates_filters_on_status_only_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor(rows=[(1, 3, "boom"), (2, None, None)])
    monkeypatch.setattr(base_state_module, "get_db", lambda: _RecordingStateDb(cursor))
    state = MatchIngestionState()

    rows = state.fetch_requeue_candidates("failed")

    assert rows == [(1, 3, "boom"), (2, None, None)]
    assert cursor.execute_query is not None
    assert "SELECT match_id, failure_count, last_error_message" in cursor.execute_query
    assert "FROM match_ingestion_state" in cursor.execute_query
    assert "WHERE status = %s" in cursor.execute_query
    assert "ORDER BY priority DESC, first_seen_at ASC" in cursor.execute_query
    assert "LIMIT" not in cursor.execute_query
    assert "match_id = %s" not in cursor.execute_query
    assert cursor.execute_values == ("failed",)


def test_fetch_requeue_candidates_applies_id_and_limit_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor(rows=[(42, 1, "boom")])
    monkeypatch.setattr(base_state_module, "get_db", lambda: _RecordingStateDb(cursor))
    state = MatchIngestionState()

    rows = state.fetch_requeue_candidates("dead", limit=5, id_value=42)

    assert rows == [(42, 1, "boom")]
    assert cursor.execute_query is not None
    assert "AND match_id = %s" in cursor.execute_query
    assert "LIMIT %s" in cursor.execute_query
    assert cursor.execute_values == ("dead", 42, 5)


def test_fetch_requeue_candidates_wraps_db_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(base_state_module, "get_db", lambda: _FailingStateDb())
    state = MatchIngestionState()

    with pytest.raises(
        MatchIngestionStateError,
        match="Failed to fetch requeue candidates from match_ingestion_state.",
    ):
        state.fetch_requeue_candidates("failed")


def test_requeue_resets_status_and_preserves_failure_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor(rowcount=2)
    monkeypatch.setattr(base_state_module, "get_db", lambda: _RecordingStateDb(cursor))
    state = MatchIngestionState()

    requeued = state.requeue([1, 2], "failed")

    assert requeued == 2
    assert cursor.execute_query is not None
    assert "SET status = 'discovered', last_updated_at = %s" in cursor.execute_query
    assert "WHERE match_id = ANY(%s) AND status = %s" in cursor.execute_query
    assert "failure_count" not in cursor.execute_query
    assert "last_error_message" not in cursor.execute_query
    assert cursor.execute_values is not None
    assert cursor.execute_values[1:] == ([1, 2], "failed")


def test_requeue_with_no_ids_is_a_no_op(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = _RecordingCursor()
    db = _RecordingStateDb(cursor)
    monkeypatch.setattr(base_state_module, "get_db", lambda: db)
    state = MatchIngestionState()

    assert state.requeue([], "failed") == 0
    assert db.cursor_uses == 0


def test_requeue_wraps_db_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(base_state_module, "get_db", lambda: _FailingStateDb())
    state = MatchIngestionState()

    with pytest.raises(
        MatchIngestionStateError,
        match="Failed to requeue items in match_ingestion_state.",
    ):
        state.requeue([1], "failed")
