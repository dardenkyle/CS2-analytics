from cs2_analytics.storage import database as database_module


class _RecordingCursor:
    def __init__(self) -> None:
        self.executed_sql: str | None = None

    def execute(self, sql: str) -> None:
        self.executed_sql = sql


class _RecordingConnection:
    def __init__(self) -> None:
        self.cursor_obj = _RecordingCursor()
        self.committed = False

    def cursor(self) -> _RecordingCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True


class _RecordingPool:
    def __init__(self) -> None:
        self.conn = _RecordingConnection()
        self.released = False

    def getconn(self) -> _RecordingConnection:
        return self.conn

    def putconn(self, conn: _RecordingConnection) -> None:
        self.released = True


def test_database_init_does_not_create_indexes(monkeypatch) -> None:
    pool = _RecordingPool()
    create_indexes_called = False

    def fail_if_called(_self) -> bool:
        nonlocal create_indexes_called
        create_indexes_called = True
        return True

    monkeypatch.setattr(database_module, "_initialize_db_pool", lambda: pool)
    monkeypatch.setattr(database_module.Database, "create_indexes", fail_if_called)

    database_module.Database()

    assert create_indexes_called is False


def test_create_indexes_uses_current_schema_indexes_without_alter_table(
    monkeypatch,
) -> None:
    pool = _RecordingPool()
    monkeypatch.setattr(database_module, "_initialize_db_pool", lambda: pool)

    db = database_module.Database()

    assert db.create_indexes() is True

    index_sql = pool.conn.cursor_obj.executed_sql
    assert index_sql is not None
    assert "ALTER TABLE" not in index_sql
    assert "idx_matches_date" in index_sql
    assert "idx_maps_match_id" in index_sql
    assert "idx_players_map_id" in index_sql
    assert "idx_match_ingestion_state_pending" in index_sql
    assert "idx_map_ingestion_state_pending" in index_sql
    assert "idx_demo_ingestion_state_pending" in index_sql
    assert pool.conn.committed is True
    assert pool.released is True
