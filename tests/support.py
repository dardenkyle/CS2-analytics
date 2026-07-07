"""Shared test fakes for transaction-aware stage-service wiring."""

from contextlib import contextmanager


class FakeCursor:
    """Records executed statements; stands in for a psycopg2 cursor."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []

    def execute(self, query: str, params: object = None) -> None:
        self.executed.append((query, params))


class FakeTransactionDb:
    """Fake Database exposing transaction(); records yielded cursors.

    Set fail_on_exit to raise after the block runs, simulating a commit
    failure so rollback paths can be exercised.
    """

    def __init__(self, fail_on_exit: Exception | None = None) -> None:
        self.cursors: list[FakeCursor] = []
        self.fail_on_exit = fail_on_exit

    @contextmanager
    def transaction(self):
        cur = FakeCursor()
        self.cursors.append(cur)
        yield cur
        if self.fail_on_exit is not None:
            raise self.fail_on_exit
