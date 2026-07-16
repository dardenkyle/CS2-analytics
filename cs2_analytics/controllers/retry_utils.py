"""Shared retry and recovery helpers for controller orchestration."""

import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

from cs2_analytics.exceptions import RetryableScrapeError


@dataclass
class BatchRunState[ScraperT]:
    """Tracks the active scraper and outcome counters for one controller batch run."""

    scraper: ScraperT
    succeeded: int = 0
    failed: int = 0
    retries: int = 0
    processed_since_reset: int = 0
    consecutive_recoverable_errors: int = 0


def is_retryable_scraper_error(error: Exception) -> bool:
    """Returns True when a scrape failure should trigger controller retry logic."""
    return isinstance(error, RetryableScrapeError)


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
