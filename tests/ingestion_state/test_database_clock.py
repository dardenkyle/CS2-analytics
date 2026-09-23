"""The ingestion-state writers stamp rows with the database clock (#213).

No lifecycle statement may pass a client-side timestamp: the stored
instant must not depend on the writing machine's clock or timezone, so
every timestamp column is set to the database's now() in the SQL itself.
"""

import datetime as dt
from contextlib import contextmanager

import pytest

from cs2_analytics.ingestion_state import base_ingestion_state as base_state_module
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState
from cs2_analytics.ingestion_state.map_ingestion_state import MapIngestionState
from cs2_analytics.ingestion_state.match_ingestion_state import MatchIngestionState

TIMESTAMP_COLUMNS = (
    "first_seen_at",
    "last_seen_at",
    "last_attempted_at",
    "last_processed_at",
    "last_failed_at",
    "last_updated_at",
)


class _RecordingCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []
        self.rowcount = 0

    def execute(self, query: str, params: object = None) -> None:
        self.executed.append((query, params))

    def executemany(self, query: str, values: list[object]) -> None:
        for params in values:
            self.executed.append((query, params))

    def fetchone(self) -> tuple[bool]:
        return (True,)


class _RecordingDb:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor = cursor

    @contextmanager
    def get_cursor(self):
        yield self.cursor


@pytest.fixture()
def cursor(monkeypatch) -> _RecordingCursor:
    recording = _RecordingCursor()
    monkeypatch.setattr(base_state_module, "get_db", lambda: _RecordingDb(recording))
    return recording


def _assert_database_clock(executed: list[tuple[str, object]]) -> None:
    assert executed, "no statement was executed"
    for query, params in executed:
        touched = [column for column in TIMESTAMP_COLUMNS if column in query]
        assert touched, query
        for column in touched:
            assert f"{column} = now()" in query or "now(), now(), now()" in query, (
                column,
                query,
            )
        for value in params or ():
            assert not isinstance(value, dt.datetime), (value, query)


def _generic_state() -> BaseIngestionState[int]:
    return BaseIngestionState("demo_ingestion_state", "demo_id", "demo_url")


@pytest.mark.parametrize(
    "operation",
    [
        lambda s: s.queue(1, "https://example.test/1", source="t"),
        lambda s: s.record_many([(1, "https://example.test/1")], source="t"),
        lambda s: s.mark_as_processing(1),
        lambda s: s.mark_as_processed(1),
        lambda s: s.mark_as_failed(1, "boom"),
        lambda s: s.mark_as_dead(1, "gone"),
        lambda s: s.mark_as_skipped(1, "skip"),
        lambda s: s.release_orphaned_processing(),
        lambda s: s.requeue([1], "failed"),
    ],
    ids=[
        "queue",
        "record_many",
        "mark_as_processing",
        "mark_as_processed",
        "mark_as_failed",
        "mark_as_dead",
        "mark_as_skipped",
        "release_orphaned_processing",
        "requeue",
    ],
)
def test_base_writers_use_the_database_clock(cursor, operation) -> None:
    operation(_generic_state())

    _assert_database_clock(cursor.executed)


def test_match_record_discovered_uses_the_database_clock(cursor) -> None:
    MatchIngestionState().record_discovered(
        [(1, "https://example.test/1", dt.date(2026, 9, 1))], source="t"
    )

    _assert_database_clock(cursor.executed)
    _, params = cursor.executed[0]
    assert params == (1, "https://example.test/1", dt.date(2026, 9, 1), "t", 0)


def test_match_mark_as_partial_uses_the_database_clock(cursor) -> None:
    MatchIngestionState().mark_as_partial(1)

    _assert_database_clock(cursor.executed)


def test_map_queue_uses_the_database_clock(cursor) -> None:
    MapIngestionState().queue(7, "https://example.test/7", match_id=1, map_order=2)

    _assert_database_clock(cursor.executed)
    _, params = cursor.executed[0]
    assert params == (7, "https://example.test/7", 1, 2, "unknown", 0)
