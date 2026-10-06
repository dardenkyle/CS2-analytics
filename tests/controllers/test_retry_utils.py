import pytest

from cs2_analytics.controllers import retry_utils
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
