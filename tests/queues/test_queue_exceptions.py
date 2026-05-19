from contextlib import contextmanager

import pytest

from cs2_analytics import ingestion_state as ingestion_state_package
from cs2_analytics.exceptions import MatchQueueError
from cs2_analytics.ingestion_state import MatchIngestionState
from cs2_analytics.ingestion_state import base_ingestion_state as base_state_module
from cs2_analytics.ingestion_state.demo_ingestion_state import DemoIngestionState
from cs2_analytics.ingestion_state.map_ingestion_state import MapIngestionState
from cs2_analytics.ingestion_state.match_ingestion_state import (
    MatchIngestionState as ConcreteMatchIngestionState,
)


class _FailingQueueDb:
    @contextmanager
    def get_cursor(self):
        raise RuntimeError("db down")
        yield


class _RecordingCursor:
    def __init__(self) -> None:
        self.execute_query: str | None = None
        self.execute_values: tuple[object, ...] | None = None
        self.executemany_query: str | None = None
        self.executemany_values: list[tuple[object, ...]] | None = None

    def execute(self, query: str, values: tuple[object, ...]) -> None:
        self.execute_query = query
        self.execute_values = values

    def executemany(self, query: str, values: list[tuple[object, ...]]) -> None:
        self.executemany_query = query
        self.executemany_values = values


class _RecordingQueueDb:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor = cursor

    @contextmanager
    def get_cursor(self):
        yield self.cursor


def test_match_queue_wraps_db_failures_in_typed_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(base_state_module, "db", _FailingQueueDb())
    queue = MatchIngestionState()

    with pytest.raises(
        MatchQueueError,
        match="Failed to queue ingestion state items in match_ingestion_state.",
    ):
        queue.queue_many([(1, "https://www.hltv.org/matches/1/test")])


def test_ingestion_state_classes_use_ingestion_state_tables() -> None:
    match_state = ConcreteMatchIngestionState()
    map_state = MapIngestionState()
    demo_state = DemoIngestionState()

    assert match_state.table_name == "match_ingestion_state"
    assert match_state.id_field == "match_id"
    assert match_state.url_field == "match_url"

    assert map_state.table_name == "map_ingestion_state"
    assert map_state.id_field == "map_id"
    assert map_state.url_field == "map_url"

    assert demo_state.table_name == "demo_ingestion_state"
    assert demo_state.id_field == "demo_id"
    assert demo_state.url_field == "demo_url"


def test_ingestion_state_package_re_exports_concrete_classes() -> None:
    assert ingestion_state_package.MatchIngestionState is ConcreteMatchIngestionState
    assert ingestion_state_package.MapIngestionState is MapIngestionState
    assert ingestion_state_package.DemoIngestionState is DemoIngestionState
    assert ingestion_state_package.__all__ == [
        "DemoIngestionState",
        "MapIngestionState",
        "MatchIngestionState",
    ]


def test_match_ingestion_state_refreshes_existing_rows_on_rediscovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(base_state_module, "db", _RecordingQueueDb(cursor))
    state = MatchIngestionState()

    state.queue(1, "https://www.hltv.org/matches/1/test", source="results")

    assert cursor.execute_query is not None
    assert "match_ingestion_state" in cursor.execute_query
    assert "'pending'" in cursor.execute_query
    assert "first_seen_at" in cursor.execute_query
    assert "last_seen_at" in cursor.execute_query
    assert "ON CONFLICT (match_id) DO UPDATE" in cursor.execute_query
    assert "last_seen_at = EXCLUDED.last_seen_at" in cursor.execute_query
    assert cursor.execute_values is not None
    assert cursor.execute_values[:4] == (
        1,
        "https://www.hltv.org/matches/1/test",
        "results",
        0,
    )


def test_match_ingestion_state_marks_failures_with_lifecycle_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(base_state_module, "db", _RecordingQueueDb(cursor))
    state = MatchIngestionState()

    state.mark_as_failed(1, "boom")

    assert cursor.execute_query is not None
    assert "status = 'failed'" in cursor.execute_query
    assert "last_failed_at" in cursor.execute_query
    assert "last_error_message" in cursor.execute_query
    assert "failure_count = COALESCE(failure_count, 0) + 1" in cursor.execute_query
    assert cursor.execute_values is not None
    assert cursor.execute_values[2:] == ("boom", 1)


def test_map_ingestion_state_queues_parent_match_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(base_state_module, "db", _RecordingQueueDb(cursor))
    state = MapIngestionState()

    state.queue(
        1,
        "https://www.hltv.org/stats/matches/mapstatsid/1/test",
        source="match_parser",
        match_id=1,
        map_order=1,
    )

    assert cursor.execute_query is not None
    assert "map_ingestion_state" in cursor.execute_query
    assert "match_id" in cursor.execute_query
    assert "map_order" in cursor.execute_query
    assert "match_id = COALESCE(EXCLUDED.match_id, map_ingestion_state.match_id)" in (
        cursor.execute_query
    )
    assert "map_order = COALESCE(EXCLUDED.map_order, map_ingestion_state.map_order)" in (
        cursor.execute_query
    )
    assert cursor.execute_values is not None
    assert cursor.execute_values[:6] == (
        1,
        "https://www.hltv.org/stats/matches/mapstatsid/1/test",
        1,
        1,
        "match_parser",
        0,
    )
