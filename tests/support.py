"""Shared test fakes for transaction-aware stage-service wiring."""

from contextlib import contextmanager

from cs2_analytics.exceptions import DatabaseOperationError


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


LOCAL_DB_HOSTS = ("localhost", "127.0.0.1", "db")

NO_TEST_DB_REASON = (
    "the local test database is not running; start it with `docker compose "
    "-f docker-compose.yml -f docker-compose.test.yml up -d db` (README: Run Tests)"
)


def open_test_database():
    """Connect to the local test database pinned by tests/conftest.py.

    Returns a Database, or None when the local Postgres is not reachable
    so callers can skip. Refuses outright if the configured host is not
    local: conftest already guarantees this under pytest, and this check
    extends the same guarantee to the unittest entry point of
    tests/storage/test_database.py, which conftest does not cover. A
    reachable but unmigrated database is migrated here, on first use:
    the host has passed the local-only guard twice by this point, so the
    migration cannot reach anything but the disposable test database,
    and no manual migration command needs to exist for it.
    """
    from cs2_analytics.config.config import DB_HOST
    from cs2_analytics.exceptions import DatabaseConnectionError
    from cs2_analytics.storage.database import Database

    if DB_HOST not in LOCAL_DB_HOSTS:
        raise RuntimeError(
            f"DB_HOST={DB_HOST!r} is not a local database host {LOCAL_DB_HOSTS};"
            " refusing to open a test database connection."
        )
    try:
        database = Database()
    except DatabaseConnectionError:
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
