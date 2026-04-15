import pytest

from cs2_analytics.controllers import results_controller as results_module
from cs2_analytics.exceptions import SessionScrapeError


class _RetryThenSucceedScraper:
    def __init__(self) -> None:
        self.run_calls = 0
        self.close_calls = 0

    def run(self, max_matches: int = 50) -> None:
        self.run_calls += 1
        if self.run_calls == 1:
            raise SessionScrapeError("Session dropped while fetching results page.")

    def close(self) -> None:
        self.close_calls += 1


def test_results_controller_retries_retryable_scrape_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(results_module, "ResultsScraper", _RetryThenSucceedScraper)
    monkeypatch.setattr(results_module.time, "sleep", lambda *_args, **_kwargs: None)

    controller = results_module.ResultsController()
    monkeypatch.setattr(controller, "_reset_scraper", lambda scraper: scraper)

    controller.run(max_matches=25)

    assert controller.scraper.run_calls == 2
