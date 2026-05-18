import pytest

from cs2_analytics.controllers import retry_utils
from cs2_analytics.exceptions import MatchQueueError, SessionScrapeError


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


class _FailingQueue:
    def mark_as_failed(self, item_id: int, reason: str) -> None:
        raise MatchQueueError("Failed to mark item as failed in match_ingestion_state.")


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


def test_mark_item_failed_propagates_queue_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _Logger()
    error = SessionScrapeError("Failed to fetch match page: https://www.hltv.org")

    with pytest.raises(
        MatchQueueError, match="Failed to mark item as failed in match_ingestion_state."
    ):
        retry_utils.mark_item_failed(
            _FailingQueue(),
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
