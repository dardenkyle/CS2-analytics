import pytest

from cs2_analytics.controllers import map_controller, match_controller, retry_utils
from cs2_analytics.exceptions import (
    DatabaseConnectionError,
    DatabaseOperationError,
    MatchIngestionStateError,
    MatchStorageError,
    SessionScrapeError,
)


class _Logger:
    def __init__(self) -> None:
        self.infos: list[tuple[str, object]] = []
        self.warnings: list[tuple[str, object]] = []
        self.exceptions: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def info(self, message: str, *args: object) -> None:
        self.infos.append((message, *args))

    def warning(self, message: str, *args: object) -> None:
        self.warnings.append((message, *args))

    def exception(self, *args: object, **kwargs: object) -> None:
        self.exceptions.append((args, kwargs))


class _Scraper:
    def __init__(self, name: str, close_error: Exception | None = None) -> None:
        self.name = name
        self.close_calls = 0
        self.close_error = close_error

    def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


class _FailingState:
    def mark_as_failed(self, item_id: int, reason: str) -> None:
        raise MatchIngestionStateError(
            "Failed to mark item as failed in match_ingestion_state."
        )


def test_reset_scraper_retries_until_health_check_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(retry_utils.time, "sleep", lambda *_args, **_kwargs: None)
    logger = _Logger()
    original = _Scraper("original")
    created: list[_Scraper] = []
    health_checks = iter([False, True])

    def scraper_factory() -> _Scraper:
        scraper = _Scraper(f"generated-{len(created) + 1}")
        created.append(scraper)
        return scraper

    def health_check(scraper: _Scraper) -> bool:
        return next(health_checks)

    recovered = retry_utils.reset_scraper(
        original,
        scraper_factory,
        logger=logger,
        close_warning_message="Failed to close scraper during recovery: %s",
        startup_delay_seconds=1.5,
        health_check=health_check,
        max_reset_attempts=3,
        between_attempt_delay_seconds=1.0,
        recovery_success_message="Scraper session recovered on reset attempt %d",
        not_ready_warning_message=(
            "New scraper session not ready on reset attempt %d/%d; retrying reset"
        ),
    )

    assert recovered is created[1]
    assert original.close_calls == 1
    assert created[0].close_calls == 1
    assert logger.warnings == [
        (
            "New scraper session not ready on reset attempt %d/%d; retrying reset",
            1,
            3,
        )
    ]
    assert logger.infos == [("Scraper session recovered on reset attempt %d", 2)]


def test_mark_item_failed_propagates_ingestion_state_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _Logger()
    error = SessionScrapeError("Failed to fetch match page: https://www.hltv.org")

    with pytest.raises(
        MatchIngestionStateError,
        match="Failed to mark item as failed in match_ingestion_state.",
    ):
        retry_utils.mark_item_failed(
            _FailingState(),
            1,
            error,
            logger=logger,
            log_message="Error processing match %s on attempt %d/%d: %s",
            attempt=3,
            max_attempts=3,
        )

    assert logger.exceptions == []


def test_reset_scraper_warns_on_close_failure_and_returns_fallback_scraper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(retry_utils.time, "sleep", lambda *_args, **_kwargs: None)
    logger = _Logger()
    original = _Scraper("original", close_error=RuntimeError("close failed"))
    created: list[_Scraper] = []

    def scraper_factory() -> _Scraper:
        scraper = _Scraper(f"generated-{len(created) + 1}")
        created.append(scraper)
        return scraper

    fallback = retry_utils.reset_scraper(
        original,
        scraper_factory,
        logger=logger,
        close_warning_message="Failed to close scraper during recovery: %s",
        startup_delay_seconds=1.0,
        health_check=lambda scraper: False,
        max_reset_attempts=2,
        between_attempt_delay_seconds=1.0,
        not_ready_warning_message=(
            "New scraper session not ready on reset attempt %d/%d; retrying reset"
        ),
        fallback_warning_message="Returning scraper after reset retries.",
    )

    assert fallback is created[2]
    assert original.close_calls == 1
    assert created[0].close_calls == 1
    assert created[1].close_calls == 1
    assert logger.warnings[0][0] == "Failed to close scraper during recovery: %s"
    assert str(logger.warnings[0][1]) == "close failed"
    assert logger.warnings[1:] == [
        (
            "New scraper session not ready on reset attempt %d/%d; retrying reset",
            1,
            2,
        ),
        (
            "New scraper session not ready on reset attempt %d/%d; retrying reset",
            2,
            2,
        ),
        ("Returning scraper after reset retries.",),
    ]


def _wrapped(outer: Exception, inner: Exception) -> Exception:
    """Returns `outer` raised explicitly from `inner`, as storage callers do."""
    try:
        raise outer from inner
    except Exception as error:
        return error


def _raised_while_handling(outer: Exception, inner: Exception) -> Exception:
    """Returns `outer` raised during handling of `inner`, with no explicit cause."""
    try:
        try:
            raise inner
        except Exception:
            raise outer  # noqa: B904 - the implicit context is the point
    except Exception as error:
        return error


CONNECTION_LOST = DatabaseConnectionError("Database connection was lost.")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (CONNECTION_LOST, True),
        (
            _wrapped(
                MatchIngestionStateError("Failed to mark item as processed."),
                DatabaseConnectionError("Database connection was lost."),
            ),
            True,
        ),
        (
            _wrapped(
                MatchIngestionStateError("Failed to mark item as processed."),
                _wrapped(
                    MatchStorageError("Failed to store match records."),
                    DatabaseConnectionError("Database connection was lost."),
                ),
            ),
            True,
        ),
        (DatabaseOperationError("Failed during database transaction."), False),
        (
            _wrapped(
                DatabaseOperationError("Failed during database transaction."),
                MatchStorageError("Failed to store match records."),
            ),
            False,
        ),
        (SessionScrapeError("Failed to fetch match page."), False),
        (
            _raised_while_handling(
                ValueError("unrelated failure"),
                DatabaseConnectionError("Database connection was lost."),
            ),
            False,
        ),
    ],
    ids=[
        "connection-error",
        "wrapped-once",
        "wrapped-twice",
        "operation-error",
        "operation-error-wrapping-storage-error",
        "scrape-error",
        "implicit-context-only",
    ],
)
def test_is_retryable_storage_error_follows_explicit_causes(
    error: Exception, expected: bool
) -> None:
    assert retry_utils.is_retryable_storage_error(error) is expected


def test_back_off_after_storage_error_counts_retry_and_scales_the_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(retry_utils.time, "sleep", sleeps.append)
    logger = _Logger()
    original_scraper = _Scraper("original")
    run_state = retry_utils.BatchRunState(
        scraper=original_scraper, consecutive_recoverable_errors=1
    )

    retry_utils.back_off_after_storage_error(
        run_state,
        7,
        CONNECTION_LOST,
        logger=logger,
        log_message="Retryable storage error for match %s (attempt %d/%d): %s",
        attempt=2,
        max_attempts=3,
        backoff_seconds=3.0,
    )

    assert run_state.retries == 1
    assert run_state.scraper is original_scraper
    assert original_scraper.close_calls == 0
    assert run_state.consecutive_recoverable_errors == 1
    assert sleeps == [6.0]
    assert logger.warnings == [
        (
            "Retryable storage error for match %s (attempt %d/%d): %s",
            7,
            2,
            3,
            CONNECTION_LOST,
        )
    ]


class _RequeueState:
    """Ingestion-state stand-in whose requeue only resets rows it was told exist."""

    def __init__(self, resettable: set[int]) -> None:
        self.resettable = resettable
        self.requeued: list[tuple[list[int], str]] = []

    def requeue(self, ids: list[int], expected_status: str) -> int:
        self.requeued.append((list(ids), expected_status))
        return len(self.resettable.intersection(ids))


class _HaltLogger(_Logger):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[tuple[object, ...]] = []

    def error(self, message: str, *args: object) -> None:
        self.errors.append((message, *args))


def test_breaker_threshold_spans_more_than_one_item_attempt_budget() -> None:
    # A threshold within one item's budget would let a single unfetchable
    # page halt every batch that selects it first.
    assert retry_utils.CIRCUIT_BREAKER_THRESHOLD > match_controller.MAX_ATTEMPTS
    assert retry_utils.CIRCUIT_BREAKER_THRESHOLD > map_controller.MAX_ATTEMPTS


def test_breaker_trips_only_once_the_streak_reaches_the_threshold() -> None:
    run_state = retry_utils.BatchRunState(scraper=_Scraper("active"))
    error = SessionScrapeError("challenged")

    trips = [
        retry_utils.breaker_trips_on(run_state, error)
        for _ in range(retry_utils.CIRCUIT_BREAKER_THRESHOLD)
    ]

    assert trips == [False] * (retry_utils.CIRCUIT_BREAKER_THRESHOLD - 1) + [True]
    assert run_state.outcome is retry_utils.BatchOutcome.HALTED
    assert run_state.halt_error is error


def test_breaker_streak_ends_on_an_error_that_reached_the_source() -> None:
    run_state = retry_utils.BatchRunState(scraper=_Scraper("active"))
    run_state.consecutive_recoverable_errors = (
        retry_utils.CIRCUIT_BREAKER_THRESHOLD - 1
    )
    run_state.streak_failed_ids.append(7)

    tripped = retry_utils.breaker_trips_on(
        run_state, DatabaseConnectionError("connection lost")
    )

    assert tripped is False
    assert run_state.consecutive_recoverable_errors == 0
    assert run_state.streak_failed_ids == []
    assert run_state.outcome is retry_utils.BatchOutcome.COMPLETED


def test_halt_batch_requeues_streak_rows_and_reports_what_remains() -> None:
    logger = _HaltLogger()
    # Row 11 changed status before the halt, so only row 12 is reset.
    state = _RequeueState(resettable={12, 20})
    error = SessionScrapeError("challenged")
    run_state = retry_utils.BatchRunState(
        scraper=_Scraper("active"),
        succeeded=6,
        failed=3,
        consecutive_recoverable_errors=retry_utils.CIRCUIT_BREAKER_THRESHOLD,
        rotations=2,
        processed_since_reset=4,
        streak_failed_ids=[11, 12],
        halt_error=error,
    )

    retry_utils.halt_batch(
        state,
        run_state,
        20,
        logger=logger,
        stage_label="MapController",
        selected=25,
    )

    assert state.requeued == [([20], "processing"), ([11, 12], "failed")]
    assert run_state.failed == 2
    assert [call[1:] for call in logger.errors] == [
        (
            "MapController",
            retry_utils.CIRCUIT_BREAKER_THRESHOLD,
            retry_utils.CIRCUIT_BREAKER_THRESHOLD,
            2,
            4,
            error,
        )
    ]
    assert [call[1:] for call in logger.warnings] == [("MapController", 1, 1, 17, 25)]
