import builtins
import io
from pathlib import Path

import pytest

from cs2_analytics.exceptions import DatabaseOperationError
from cs2_analytics.storage import initialize_db as initialize_db_module

SCHEMA_PATH = Path(__file__).parents[2] / "cs2_analytics" / "storage" / "schema.sql"


class _RecordingCursor:
    def __init__(
        self,
        should_fail: bool = False,
        fetchone_response: tuple[int] | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.fetchone_response = fetchone_response
        self.executed: list[tuple[object, object | None]] = []
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.exited = True

    def execute(self, sql: object, params: object | None = None) -> None:
        if self.should_fail:
            raise RuntimeError("schema apply failed")
        self.executed.append((sql, params))

    def fetchone(self) -> tuple[int] | None:
        return self.fetchone_response


class _RecordingConnection:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor_obj = cursor
        self.entered = False
        self.exited = False
        self.autocommit = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.exited = True

    def cursor(self) -> _RecordingCursor:
        return self.cursor_obj


class _RecordingDatabase:
    instances: list["_RecordingDatabase"] = []

    def __init__(self) -> None:
        self.indexes_created = False
        self.closed = False
        self.instances.append(self)

    def create_indexes(self) -> bool:
        self.indexes_created = True
        return True

    def close_db_pool(self) -> None:
        self.closed = True


def _fake_schema_file(*_args, **_kwargs) -> io.StringIO:
    return io.StringIO("SELECT 1;")


def _table_definition(schema_sql: str, table_name: str) -> str:
    start_marker = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    start_index = schema_sql.index(start_marker)
    end_index = schema_sql.index("\n);", start_index)
    return schema_sql[start_index:end_index]


def test_initialize_database_executes_schema_and_creates_indexes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    connection = _RecordingConnection(cursor)
    _RecordingDatabase.instances = []

    monkeypatch.setattr(
        initialize_db_module.psycopg2, "connect", lambda **_: connection
    )
    monkeypatch.setattr(initialize_db_module, "Database", _RecordingDatabase)
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
    assert cursor.executed == [("SELECT 1;", None)]
    assert _RecordingDatabase.instances[0].indexes_created is True
    assert _RecordingDatabase.instances[0].closed is True


def test_initialize_database_can_create_configured_database_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    connection = _RecordingConnection(cursor)
    create_database_calls: list[bool] = []
    _RecordingDatabase.instances = []

    monkeypatch.setattr(
        initialize_db_module.psycopg2, "connect", lambda **_: connection
    )
    monkeypatch.setattr(initialize_db_module, "Database", _RecordingDatabase)
    monkeypatch.setattr(
        initialize_db_module,
        "create_database_if_missing",
        lambda: create_database_calls.append(True),
    )
    monkeypatch.setattr(initialize_db_module.os.path, "dirname", lambda _: "fake_dir")
    monkeypatch.setattr(builtins, "open", _fake_schema_file)

    initialize_db_module.initialize_database(create_db=True)

    assert create_database_calls == [True]
    assert cursor.executed == [("SELECT 1;", None)]
    assert _RecordingDatabase.instances[0].indexes_created is True


def test_initialize_database_wraps_schema_failures_in_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor(should_fail=True)
    connection = _RecordingConnection(cursor)

    monkeypatch.setattr(
        initialize_db_module.psycopg2, "connect", lambda **_: connection
    )
    monkeypatch.setattr(initialize_db_module, "Database", _RecordingDatabase)
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


def test_wipe_database_executes_explicit_drop_table_statements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    connection = _RecordingConnection(cursor)

    monkeypatch.setattr(
        initialize_db_module.psycopg2, "connect", lambda **_: connection
    )

    initialize_db_module.wipe_database()

    wipe_sql = cursor.executed[0][0]
    assert isinstance(wipe_sql, str)
    assert "DROP TABLE IF EXISTS demo_files CASCADE;" in wipe_sql
    assert "DROP TABLE IF EXISTS matches CASCADE;" in wipe_sql
    assert "CREATE TABLE" not in wipe_sql


def test_init_flag_runs_schema_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    initialize_calls: list[bool] = []

    monkeypatch.setattr(
        initialize_db_module,
        "initialize_database",
        lambda create_db=False: initialize_calls.append(create_db),
    )

    initialize_db_module.main(["--init"])

    assert initialize_calls == [False]


def test_default_command_still_runs_schema_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialize_calls: list[bool] = []

    monkeypatch.setattr(
        initialize_db_module,
        "initialize_database",
        lambda create_db=False: initialize_calls.append(create_db),
    )

    initialize_db_module.main([])

    assert initialize_calls == [False]


def test_create_database_flag_runs_database_creation_then_schema_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialize_calls: list[bool] = []

    monkeypatch.setattr(
        initialize_db_module,
        "initialize_database",
        lambda create_db=False: initialize_calls.append(create_db),
    )

    initialize_db_module.main(["--create-database"])

    assert initialize_calls == [True]


def test_wipe_flag_requires_confirmation_before_wiping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wipe_calls: list[bool] = []

    monkeypatch.setattr(builtins, "input", lambda _prompt: "n")
    monkeypatch.setattr(
        initialize_db_module,
        "wipe_database",
        lambda: wipe_calls.append(True),
    )

    initialize_db_module.main(["--wipe"])

    assert wipe_calls == []


def test_wipe_flag_runs_wipe_after_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wipe_calls: list[bool] = []

    monkeypatch.setattr(builtins, "input", lambda _prompt: "y")
    monkeypatch.setattr(
        initialize_db_module,
        "wipe_database",
        lambda: wipe_calls.append(True),
    )

    initialize_db_module.main(["--wipe"])

    assert wipe_calls == [True]


def test_create_database_if_missing_creates_database_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor(fetchone_response=None)
    connection = _RecordingConnection(cursor)

    monkeypatch.setattr(
        initialize_db_module.psycopg2, "connect", lambda **_: connection
    )

    initialize_db_module.create_database_if_missing()

    assert connection.autocommit is True
    assert cursor.executed[0][0] == "SELECT 1 FROM pg_database WHERE datname = %s;"
    assert cursor.executed[0][1] == (initialize_db_module.DB_NAME,)
    assert len(cursor.executed) == 2


def test_schema_defines_non_destructive_table_creation() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    assert "DROP TABLE" not in schema_sql
    assert "CREATE INDEX" not in schema_sql
    assert "CREATE TABLE IF NOT EXISTS matches" in schema_sql


def test_schema_defines_ingestion_state_tables() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    for table_name in (
        "match_ingestion_state",
        "map_ingestion_state",
        "demo_ingestion_state",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in schema_sql

    for removed_table_name in (
        "match_scrape_queue",
        "map_scrape_queue",
        "demo_scrape_queue",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {removed_table_name}" not in schema_sql

    required_columns = (
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
    )
    required_status_values = (
        "'pending'",
        "'processing'",
        "'processed'",
        "'failed'",
        "'skipped'",
    )

    for table_name in (
        "match_ingestion_state",
        "map_ingestion_state",
        "demo_ingestion_state",
    ):
        table_sql = _table_definition(schema_sql, table_name)
        for column_name in required_columns:
            assert column_name in table_sql
        for status_value in required_status_values:
            assert status_value in table_sql
        assert "retry_count" not in table_sql

    map_table_sql = _table_definition(schema_sql, "map_ingestion_state")
    assert "map_id INT PRIMARY KEY" in map_table_sql
    assert "match_id INT REFERENCES matches(match_id) ON DELETE CASCADE" in map_table_sql
    assert "map_order INT CHECK" in map_table_sql


def test_schema_defines_map_storage_contract() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    table_sql = _table_definition(schema_sql, "maps")

    required_columns = (
        "map_id INT PRIMARY KEY",
        "match_id INT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE",
        "map_url TEXT UNIQUE NOT NULL",
        "map_order INT NOT NULL CHECK",
        "map_name TEXT NOT NULL",
        "team1_score INT NOT NULL CHECK (team1_score >= 0)",
        "team2_score INT NOT NULL CHECK (team2_score >= 0)",
        "map_winner TEXT NOT NULL",
        "date TIMESTAMP NOT NULL",
        "inserted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        "last_scraped_at TIMESTAMPTZ",
        "last_updated_at TIMESTAMPTZ",
        "data_complete BOOLEAN NOT NULL DEFAULT FALSE",
        "UNIQUE (match_id, map_order)",
    )

    for column_sql in required_columns:
        assert column_sql in table_sql


def test_schema_defines_player_map_relationship() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    table_sql = _table_definition(schema_sql, "players")

    assert "map_id INT NOT NULL REFERENCES maps(map_id) ON DELETE CASCADE" in table_sql
    assert "PRIMARY KEY (map_id, player_id)" in table_sql
