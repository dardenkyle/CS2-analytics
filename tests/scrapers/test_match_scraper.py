"""Tests for the fetch-only match scraper."""

import pytest

from cs2_analytics.exceptions import MatchScrapeError
from cs2_analytics.scrapers import match_scraper as match_scraper_module
from cs2_analytics.scrapers.match_scraper import MatchScraper


class _FailingQuitDriver:
    def __init__(self, *args, **kwargs) -> None:
        self.quit_calls = 0

    def quit(self) -> None:
        self.quit_calls += 1
        raise RuntimeError("browser already gone")


def test_close_failure_raises_typed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(match_scraper_module, "Driver", _FailingQuitDriver)
    scraper = MatchScraper()

    with pytest.raises(
        MatchScrapeError, match="Failed to close match scraper driver."
    ) as exc_info:
        scraper.close()

    assert scraper.driver.quit_calls == 1
    assert isinstance(exc_info.value.__cause__, RuntimeError)
