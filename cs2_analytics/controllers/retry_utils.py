"""Shared retry and recovery helpers for controller orchestration."""

import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from enum import StrEnum

from cs2_analytics.exceptions import DatabaseConnectionError, RetryableScrapeError

# Consecutive retryable scraper errors, with no successful fetch between
# them, that halt a batch (#175, ADR-0017). An item's attempt budget is
# three, so five always spans two items: one unfetchable page cannot halt a
# batch, while a source-wide block trips partway through the second item.
CIRCUIT_BREAKER_THRESHOLD = 5


class BatchOutcome(StrEnum):
    """How a match or map batch run ended."""

    COMPLETED = "completed"
    HALTED = "halted"


@dataclass
class BatchRunState[ScraperT]:
    """Tracks the active scraper and outcome counters for one controller batch run.

    `consecutive_recoverable_errors` counts retryable scraper errors since
    the last fetch that reached the source, across items; it drives the
    circuit breaker. `streak_failed_ids` holds the rows that exhausted
    their attempts inside that streak, so a halt can return them to the
    queue.
    """

    scraper: ScraperT
    succeeded: int = 0
    failed: int = 0
    retries: int = 0
    processed_since_reset: int = 0
    consecutive_recoverable_errors: int = 0
    rotations: int = 0
    streak_failed_ids: list[int | str] = field(default_factory=list)
    halt_error: Exception | None = None

    @property
    def outcome(self) -> BatchOutcome:
        """Reports whether the circuit breaker halted the batch."""
        if self.halt_error is not None:
            return BatchOutcome.HALTED
        return BatchOutcome.COMPLETED


def is_retryable_scraper_error(error: Exception) -> bool:
    """Returns True when a scrape failure should trigger controller retry logic."""
    return isinstance(error, RetryableScrapeError)


def is_retryable_storage_error(error: Exception) -> bool:
    """Returns True when a lost database connection caused the failure.

    The storage layer raises `DatabaseConnectionError` for a connection it
    could not acquire or that dropped mid-operation. Storage and
    ingestion-state callers may wrap it, so the explicit cause chain is
    checked as well. Every other storage failure stays non-retryable.
    """
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, DatabaseConnectionError):
            return True
        current = current.__cause__
    return False


def breaker_trips_on(run_state: BatchRunState, error: Exception) -> bool:
    """Updates the blocked-fetch streak for one failed attempt.

    A retryable scraper error extends the streak and returns True once it
    reaches `CIRCUIT_BREAKER_THRESHOLD`. Any other error means the fetch
    reached the source, so it ends the streak the same way a success does.
    """
    if not is_retryable_scraper_error(error):
        clear_blocked_streak(run_state)
        return False
    run_state.consecutive_recoverable_errors += 1
    if run_state.consecutive_recoverable_errors < CIRCUIT_BREAKER_THRESHOLD:
        return False
    run_state.halt_error = error
    return True


def clear_blocked_streak(run_state: BatchRunState) -> None:
    """Ends the blocked-fetch streak after a fetch that reached the source."""
    run_state.consecutive_recoverable_errors = 0
    run_state.streak_failed_ids.clear()


def halt_batch(
    state,
    run_state: BatchRunState,
    in_flight_id: int | str,
    *,
    logger,
    stage_label: str,
    selected: int,
) -> None:
    """Logs a circuit-breaker halt and returns the streak's rows to the queue.

    The in-flight row never finished, and the rows the streak marked
    failed were blocked rather than broken, so both go back to
    'discovered' and a halted run needs no manual requeue. failure_count
    and last_error_message stay on those rows as history.
    """
    logger.error(
        "%s circuit breaker tripped: %d consecutive retryable scraper errors "
        "(threshold %d); halting the batch. rotations=%d "
        "processed_since_rotation=%d last_error=%s",
        stage_label,
        run_state.consecutive_recoverable_errors,
        CIRCUIT_BREAKER_THRESHOLD,
        run_state.rotations,
        run_state.processed_since_reset,
        run_state.halt_error,
    )
    released = state.requeue([in_flight_id], "processing")
    requeued = state.requeue(list(run_state.streak_failed_ids), "failed")
    run_state.failed -= requeued
    logger.warning(
        "%s halt returned %d in-flight and %d failed row(s) to 'discovered'; "
        "%d of %d selected row(s) remain for the next run.",
        stage_label,
        released,
        requeued,
        selected - run_state.succeeded - run_state.failed,
        selected,
    )


def _close_before_reset(scraper, logger, close_warning_message: str) -> None:
    """Closes the outgoing scraper, downgrading close failures to a warning."""
    try:
        scraper.close()
    except Exception as e:
        logger.warning(close_warning_message, e)


def _build_scraper[ScraperT](
    scraper_factory: Callable[[], ScraperT], startup_delay_seconds: float
) -> ScraperT:
    """Creates a scraper and waits out its session startup delay."""
    new_scraper = scraper_factory()
    time.sleep(startup_delay_seconds)
    return new_scraper


def _discard_unready_scraper(
    new_scraper,
    *,
    logger,
    not_ready_warning_message: str | None,
    reset_attempt: int,
    attempt_total: int,
) -> None:
    """Logs and closes a fresh scraper that failed its health check."""
    if not_ready_warning_message:
        logger.warning(not_ready_warning_message, reset_attempt, attempt_total)
    with suppress(Exception):
        new_scraper.close()


def reset_scraper[ScraperT](
    scraper: ScraperT,
    scraper_factory: Callable[[], ScraperT],
    *,
    logger,
    close_warning_message: str,
    startup_delay_seconds: float = 1.0,
    health_check: Callable[[ScraperT], bool] | None = None,
    max_reset_attempts: int = 1,
    between_attempt_delay_seconds: float = 1.0,
    recovery_success_message: str | None = None,
    not_ready_warning_message: str | None = None,
    fallback_warning_message: str | None = None,
    fallback_delay_seconds: float | None = None,
) -> ScraperT:
    """Closes and recreates a scraper, optionally retrying until a health check passes."""
    _close_before_reset(scraper, logger, close_warning_message)

    attempt_total = max(1, max_reset_attempts)

    for reset_attempt in range(1, attempt_total + 1):
        new_scraper = _build_scraper(scraper_factory, startup_delay_seconds)

        if health_check is None or health_check(new_scraper):
            if recovery_success_message and reset_attempt > 1:
                logger.info(recovery_success_message, reset_attempt)
            return new_scraper

        _discard_unready_scraper(
            new_scraper,
            logger=logger,
            not_ready_warning_message=not_ready_warning_message,
            reset_attempt=reset_attempt,
            attempt_total=attempt_total,
        )

        if reset_attempt < attempt_total:
            time.sleep(between_attempt_delay_seconds)

    if fallback_warning_message:
        logger.warning(fallback_warning_message)

    return _build_scraper(
        scraper_factory,
        startup_delay_seconds
        if fallback_delay_seconds is None
        else fallback_delay_seconds,
    )


def back_off_after_storage_error(
    run_state: BatchRunState,
    item_id: int | str,
    error: Exception,
    *,
    logger,
    log_message: str,
    attempt: int,
    max_attempts: int,
    backoff_seconds: float,
) -> None:
    """Counts a retry and waits before the next attempt at the same item.

    The scraper is left alone: the session was not at fault, so it is not
    reset and the error does not count toward scraper cooldowns.
    """
    run_state.retries += 1
    logger.warning(log_message, item_id, attempt, max_attempts, error)
    time.sleep(backoff_seconds * attempt)


def mark_item_failed(
    state,
    item_id: int | str,
    error: Exception,
    *,
    logger,
    log_message: str,
    attempt: int,
    max_attempts: int,
    reason_limit: int = 500,
) -> None:
    """Marks an ingestion-state item failed, then logs the terminal controller exception."""
    state.mark_as_failed(item_id, str(error)[:reason_limit])
    logger.exception(log_message, item_id, attempt, max_attempts, error)
