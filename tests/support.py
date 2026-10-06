"""Shared test fakes for transaction-aware stage-service wiring."""

from contextlib import contextmanager

from cs2_analytics.exceptions import DatabaseConnectionError, DatabaseOperationError


class FakeCursor:
    """Records executed statements; stands in for a psycopg2 cursor."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []

    def execute(self, query: str, params: object = None) -> None:
        self.executed.append((query, params))


class FakeTransactionDb:
    """Fake Database exposing transaction(); records yielded cursors.

    Set fail_on_exit to raise after the block runs, simulating a commit
    failure so rollback paths can be exercised. Failures surface as
    DatabaseOperationError with the original exception as __cause__,
    matching production Database.transaction().
    """

    def __init__(self, fail_on_exit: Exception | None = None) -> None:
        self.cursors: list[FakeCursor] = []
        self.fail_on_exit = fail_on_exit

    @contextmanager
    def transaction(self):
        cur = FakeCursor()
        self.cursors.append(cur)
        try:
            yield cur
            if self.fail_on_exit is not None:
                raise self.fail_on_exit
        except Exception as e:
            raise DatabaseOperationError("Failed during database transaction.") from e


class ConnectionLossDb(FakeTransactionDb):
    """Fake Database whose first `losses` transactions lose the connection.

    A lost transaction raises DatabaseConnectionError before its block runs,
    matching what production Database.transaction() reports when the server
    closes the connection: nothing the block wrote survives. Later
    transactions behave like FakeTransactionDb.
    """

    def __init__(self, losses: int) -> None:
        super().__init__()
        self.losses = losses
        self.attempts = 0

    @contextmanager
    def transaction(self):
        self.attempts += 1
        if self.attempts <= self.losses:
            raise DatabaseConnectionError(
                "Database connection was lost during a transaction."
            )
        with super().transaction() as cur:
            yield cur


NO_TEST_DB_REASON = (
    "the local test database is not reachable (not running, or its credentials "
    "differ from .env.test); start it with `docker compose "
    "-f docker-compose.yml -f docker-compose.test.yml up -d db` (README: Run Tests)"
)


def open_test_database():
    """Connect to the local test database pinned by tests/conftest.py.

    Returns a Database, or None when the local Postgres is not reachable
    so callers can skip. Refuses outright if the configured host is not
    local. Under pytest, conftest has already pinned the host; under the
    unittest entry point of tests/storage/test_database.py, conftest does
    not run and config resolves the development environment, so this check
    is what stops that entry point from ever opening a non-local
    connection (it errors rather than skips: that is a setup mistake). A
    reachable but unmigrated database is migrated here, on first use:
    the host has passed the local-only guard twice by this point, so the
    migration cannot reach anything but the disposable test database,
    and no manual migration command needs to exist for it. The same goes
    for the database itself, which is created when the server has none by
    that name (a volume first initialized by the development stack).

    Only the `test` environment may open it. The development database is
    local too, so the host check alone would let an entry point that
    skipped conftest truncate development data (#179).
    """
    from cs2_analytics.config.config import ACTIVE_ENV, DB_HOST, LOCAL_DB_HOSTS
    from cs2_analytics.exceptions import (
        DatabaseConnectionError,
        DatabaseOperationError,
    )
    from cs2_analytics.runtime_env import RuntimeEnv
    from cs2_analytics.storage.database import Database
    from cs2_analytics.storage.initialize_db import create_database_if_missing

    if DB_HOST not in LOCAL_DB_HOSTS:
        raise RuntimeError(
            f"DB_HOST={DB_HOST!r} is not a local database host {sorted(LOCAL_DB_HOSTS)};"
            " refusing to open a test database connection."
        )
    if ACTIVE_ENV is not RuntimeEnv.TEST:
        raise RuntimeError(
            f"The {ACTIVE_ENV.value} environment is active; refusing to open a test"
            " database connection outside the test environment (run under pytest,"
            " or set CS2A_ENV=test)."
        )
    try:
        create_database_if_missing()
        database = Database()
    except (DatabaseConnectionError, DatabaseOperationError):
        return None
    _ensure_migrated_schema(database)
    return database


def _schema_present(database) -> bool:
    with database.get_cursor() as cur:
        cur.execute("SELECT to_regclass('public.alembic_version');")
        (present,) = cur.fetchone()
    return present is not None


def _ensure_migrated_schema(database) -> None:
    """Run the Alembic migrations against the (local-only) test database."""
    from cs2_analytics.storage.initialize_db import run_migrations

    if _schema_present(database):
        return
    run_migrations()
    if not _schema_present(database):
        raise RuntimeError("migrating the local test database left no schema behind.")
