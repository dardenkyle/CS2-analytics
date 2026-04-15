import io
import builtins

import pytest

from cs2_analytics.exceptions import DatabaseOperationError
from cs2_analytics.storage import initialize_db as initialize_db_module


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
        lambda *args, **kwargs: io.StringIO("SELECT 1;"),
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
        lambda *args, **kwargs: io.StringIO("SELECT 1;"),
    )

    with pytest.raises(
        DatabaseOperationError, match="Failed to initialize database schema."
    ) as exc_info:
        initialize_db_module.initialize_database()

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert connection.exited is True
    assert cursor.exited is True
