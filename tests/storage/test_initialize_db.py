import builtins
import io
from pathlib import Path

import pytest

from cs2_analytics.exceptions import DatabaseOperationError
from cs2_analytics.storage import initialize_db as initialize_db_module

SCHEMA_PATH = Path(__file__).parents[2] / "cs2_analytics" / "storage" / "schema.sql"


class _RecordingCursor:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.executed_sql: str | None = None
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.exited = True

    def execute(self, sql: str) -> None:
        if self.should_fail:
            raise RuntimeError("schema apply failed")
        self.executed_sql = sql


class _RecordingConnection:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor_obj = cursor
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.exited = True

    def cursor(self) -> _RecordingCursor:
        return self.cursor_obj


def _fake_schema_file(*_args, **_kwargs) -> io.StringIO:
    return io.StringIO("SELECT 1;")


def test_initialize_database_executes_schema_with_context_managers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    connection = _RecordingConnection(cursor)

    monkeypatch.setattr(initialize_db_module.psycopg2, "connect", lambda **_: connection)
    monkeypatch.setattr(initialize_db_module.os.path, "dirname", lambda _: "fake_dir")
    monkeypatch.setattr(
        builtins,
        "open",
        _fake_schema_file,
    )

    initialize_db_module.initialize_database()

    assert connection.entered is True
    assert connection.exited is True
    assert cursor.entered is True
    assert cursor.exited is True
    assert cursor.executed_sql == "SELECT 1;"


def test_initialize_database_wraps_schema_failures_in_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor(should_fail=True)
    connection = _RecordingConnection(cursor)

    monkeypatch.setattr(initialize_db_module.psycopg2, "connect", lambda **_: connection)
    monkeypatch.setattr(initialize_db_module.os.path, "dirname", lambda _: "fake_dir")
    monkeypatch.setattr(
        builtins,
        "open",
        _fake_schema_file,
    )

    with pytest.raises(
        DatabaseOperationError, match="Failed to initialize database schema."
    ) as exc_info:
        initialize_db_module.initialize_database()

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert connection.exited is True
    assert cursor.exited is True


def test_schema_defines_ingestion_state_tables() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    for table_name in (
        "match_ingestion_state",
        "map_ingestion_state",
        "demo_ingestion_state",
    ):
        assert f"CREATE TABLE {table_name}" in schema_sql

    for old_table_name in (
        "match_scrape_queue",
        "map_scrape_queue",
        "demo_scrape_queue",
    ):
        assert f"CREATE TABLE {old_table_name}" not in schema_sql

    for column_name in (
        "status",
        "first_seen_at",
        "last_seen_at",
        "last_attempted_at",
        "last_processed_at",
        "last_failed_at",
        "failure_count",
        "last_error_message",
        "source",
        "priority",
        "last_updated_at",
    ):
        assert column_name in schema_sql

    assert "'pending'" in schema_sql
    assert "'processing'" in schema_sql
    assert "'processed'" in schema_sql
    assert "'failed'" in schema_sql
    assert "'skipped'" in schema_sql
    assert "retry_count" not in schema_sql
