"""Shared retry and recovery helpers for controller orchestration."""

import time
from collections.abc import Callable
from contextlib import suppress
from typing import TypeVar

from cs2_analytics.exceptions import RetryableScrapeError

ScraperT = TypeVar("ScraperT")


def is_retryable_scraper_error(error: Exception) -> bool:
    """Returns True when a scrape failure should trigger controller retry logic."""
    return isinstance(error, RetryableScrapeError)


def reset_scraper(
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
    try:
        scraper.close()
    except Exception as e:
        logger.warning(close_warning_message, e)

    attempt_total = max(1, max_reset_attempts)

    for reset_attempt in range(1, attempt_total + 1):
        new_scraper = scraper_factory()
        time.sleep(startup_delay_seconds)

        if health_check is None or health_check(new_scraper):
            if recovery_success_message and reset_attempt > 1:
                logger.info(recovery_success_message, reset_attempt)
            return new_scraper

        if not_ready_warning_message:
            logger.warning(not_ready_warning_message, reset_attempt, attempt_total)

        with suppress(Exception):
            new_scraper.close()

        if reset_attempt < attempt_total:
            time.sleep(between_attempt_delay_seconds)

    if fallback_warning_message:
        logger.warning(fallback_warning_message)

    fallback_scraper = scraper_factory()
    time.sleep(
        startup_delay_seconds
        if fallback_delay_seconds is None
        else fallback_delay_seconds
    )
    return fallback_scraper


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
