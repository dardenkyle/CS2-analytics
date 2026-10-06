"""Connection-loss classification in the Database cursor helpers (#208).

A connection the server has closed cannot roll back; before #208 the
rollback raised a second driver error that replaced the original one and
reached controllers unclassified. The unit tests drive `transaction()` and
`get_cursor()` with a stub connection. The integration tests terminate a
real backend on the local test database (session `test_database` fixture,
see tests/conftest.py) and skip when it is not running.
"""

import psycopg2
import pytest

from cs2_analytics.exceptions import DatabaseConnectionError, DatabaseOperationError
from cs2_analytics.storage.database import Database

CURSOR_HELPERS = ["transaction", "get_cursor"]
CONNECTION_CLOSED = 2


class _StubCursor:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _StubConnection:
    def __init__(self, rollback_error: Exception | None = None) -> None:
        self.closed = 0
        self.rollback_error = rollback_error
        self.rollback_calls = 0
        self.commit_calls = 0

    def cursor(self) -> _StubCursor:
        return _StubCursor()

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1
        if self.rollback_error is not None:
            raise self.rollback_error


class _StubPool:
    def __init__(self, conn: _StubConnection) -> None:
        self.conn = conn
        self.released: list[_StubConnection] = []

    def getconn(self) -> _StubConnection:
        return self.conn

    def putconn(self, conn: _StubConnection) -> None:
        self.released.append(conn)


def _database_over(conn: _StubConnection) -> tuple[Database, _StubPool]:
    """Builds a Database around a stub pool, skipping real pool startup."""
    pool = _StubPool(conn)
    database = Database.__new__(Database)
    database.pool = pool  # type: ignore[assignment]
    return database, pool


@pytest.mark.parametrize("helper", CURSOR_HELPERS)
def test_closed_connection_raises_connection_error_without_rollback(
    helper: str,
) -> None:
    conn = _StubConnection()
    database, pool = _database_over(conn)
    server_closed = psycopg2.OperationalError("server closed the connection")

    with (
        pytest.raises(DatabaseConnectionError) as exc_info,
        getattr(database, helper)(),
    ):
        conn.closed = CONNECTION_CLOSED
        raise server_closed

    assert exc_info.value.__cause__ is server_closed
    assert conn.rollback_calls == 0
    assert pool.released == [conn]


@pytest.mark.parametrize("helper", CURSOR_HELPERS)
def test_failed_rollback_raises_connection_error_with_the_original_cause(
    helper: str,
) -> None:
    conn = _StubConnection(
        rollback_error=psycopg2.InterfaceError("connection already closed")
    )
    database, pool = _database_over(conn)
    statement_error = psycopg2.OperationalError("server closed the connection")

    with (
        pytest.raises(DatabaseConnectionError) as exc_info,
        getattr(database, helper)(),
    ):
        raise statement_error

    assert exc_info.value.__cause__ is statement_error
    assert conn.rollback_calls == 1
    assert pool.released == [conn]


@pytest.mark.parametrize("helper", CURSOR_HELPERS)
def test_failure_on_open_connection_rolls_back_and_raises_operation_error(
    helper: str,
) -> None:
    conn = _StubConnection()
    database, pool = _database_over(conn)
    data_error = psycopg2.DataError("invalid input syntax for type integer")

    with (
        pytest.raises(DatabaseOperationError) as exc_info,
        getattr(database, helper)(),
    ):
        raise data_error

    assert not isinstance(exc_info.value, DatabaseConnectionError)
    assert exc_info.value.__cause__ is data_error
    assert conn.rollback_calls == 1
    assert conn.commit_calls == 0
    assert pool.released == [conn]


def _terminate_backend(pid: int) -> None:
    """Closes one backend of the local test database from a second connection."""
    from cs2_analytics.config.config import (
        DB_HOST,
        DB_NAME,
        DB_PASS,
        DB_PORT,
        DB_USER,
        LOCAL_DB_HOSTS,
    )

    assert DB_HOST in LOCAL_DB_HOSTS, f"refusing to terminate a backend on {DB_HOST!r}"
    admin = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    try:
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute("SELECT pg_terminate_backend(%s);", (pid,))
    finally:
        admin.close()


def _backend_pid(cur) -> int:
    cur.execute("SELECT pg_backend_pid();")
    (pid,) = cur.fetchone()
    return int(pid)


def _assert_usable(database: Database, helper: str) -> None:
    with getattr(database, helper)() as cur:
        cur.execute("SELECT 1;")
        assert cur.fetchone() == (1,)


@pytest.mark.parametrize("helper", CURSOR_HELPERS)
def test_backend_terminated_mid_operation_is_a_connection_error(
    test_database, helper: str
) -> None:
    with (
        pytest.raises(DatabaseConnectionError) as exc_info,
        getattr(test_database, helper)() as cur,
    ):
        _terminate_backend(_backend_pid(cur))
        cur.execute("SELECT 1;")

    assert isinstance(exc_info.value.__cause__, psycopg2.OperationalError)
    _assert_usable(test_database, helper)


@pytest.mark.parametrize("helper", CURSOR_HELPERS)
def test_connection_closed_while_idle_in_the_pool_is_a_connection_error(
    test_database, helper: str
) -> None:
    with test_database.get_cursor() as cur:
        idle_pid = _backend_pid(cur)
    _terminate_backend(idle_pid)

    with (
        pytest.raises(DatabaseConnectionError) as exc_info,
        getattr(test_database, helper)() as cur,
    ):
        cur.execute("SELECT 1;")

    assert isinstance(exc_info.value.__cause__, psycopg2.OperationalError)
    _assert_usable(test_database, helper)


@pytest.mark.parametrize("helper", CURSOR_HELPERS)
def test_statement_error_on_live_connection_stays_an_operation_error(
    test_database, helper: str
) -> None:
    with (
        pytest.raises(DatabaseOperationError) as exc_info,
        getattr(test_database, helper)() as cur,
    ):
        failing_pid = _backend_pid(cur)
        cur.execute("SELECT 1 / 0;")

    assert not isinstance(exc_info.value, DatabaseConnectionError)
    assert isinstance(exc_info.value.__cause__, psycopg2.DataError)
    with getattr(test_database, helper)() as cur:
        assert _backend_pid(cur) == failing_pid
