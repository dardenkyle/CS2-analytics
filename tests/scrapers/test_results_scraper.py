"""Tests for the fetch-only results scraper."""

import datetime as dt
from unittest import mock

import pytest

from cs2_analytics.exceptions import ResultsScrapeError
from cs2_analytics.scrapers import results_scraper as results_scraper_module
from cs2_analytics.scrapers.results_scraper import ResultsScraper


class _FakeDriver:
    def __init__(self, *args, **kwargs) -> None:
        self.quit_called = False

    def quit(self) -> None:
        self.quit_called = True


class _FakePageDriver:
    """Serves a fixed results page for _extract_matches_from_page tests."""

    def __init__(self, page_source: str) -> None:
        self.page_source = page_source
        self.loaded_urls: list[str] = []

    def get(self, url: str) -> None:
        self.loaded_urls.append(url)


@pytest.fixture
def scraper(monkeypatch: pytest.MonkeyPatch) -> ResultsScraper:
    monkeypatch.setattr(results_scraper_module, "Driver", _FakeDriver)
    monkeypatch.setattr(
        results_scraper_module.time, "sleep", lambda *_args, **_kwargs: None
    )
    return ResultsScraper()


def _page(urls: list[str], stop: bool) -> tuple[list[str], bool]:
    return urls, stop


def test_iter_match_batches_yields_page_batches_with_ids(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = iter(
        [
            _page(
                [
                    "https://www.hltv.org/matches/111/a-vs-b",
                    "https://www.hltv.org/matches/222/c-vs-d",
                    "https://www.hltv.org/results/not-a-match",
                ],
                stop=False,
            ),
            _page(["https://www.hltv.org/matches/333/e-vs-f"], stop=True),
        ]
    )
    monkeypatch.setattr(scraper, "_extract_matches_from_page", lambda _url: next(pages))

    batches = list(scraper.iter_match_batches(max_matches=50))

    assert batches == [
        [
            (111, "https://www.hltv.org/matches/111/a-vs-b"),
            (222, "https://www.hltv.org/matches/222/c-vs-d"),
        ],
        [(333, "https://www.hltv.org/matches/333/e-vs-f")],
    ]


def test_iter_match_batches_stops_at_max_matches(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fake_extract(_url: str) -> tuple[list[str], bool]:
        nonlocal calls
        calls += 1
        return [f"https://www.hltv.org/matches/{calls}00/x-vs-y"], False

    monkeypatch.setattr(scraper, "_extract_matches_from_page", fake_extract)

    batches = list(scraper.iter_match_batches(max_matches=2))

    assert len(batches) == 2
    assert calls == 2


def test_iter_match_batches_caps_within_a_page(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    urls = [f"https://www.hltv.org/matches/{n}/x-vs-y" for n in (101, 102, 103)]
    calls = 0

    def fake_extract(_url: str) -> tuple[list[str], bool]:
        nonlocal calls
        calls += 1
        return urls, False

    monkeypatch.setattr(scraper, "_extract_matches_from_page", fake_extract)

    batches = list(scraper.iter_match_batches(max_matches=2))

    assert batches == [
        [
            (101, "https://www.hltv.org/matches/101/x-vs-y"),
            (102, "https://www.hltv.org/matches/102/x-vs-y"),
        ]
    ]
    assert calls == 1


def test_iter_match_batches_stops_on_empty_page(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scraper, "_extract_matches_from_page", lambda _url: ([], False))

    assert list(scraper.iter_match_batches(max_matches=10)) == []


def test_extract_match_id(scraper: ResultsScraper) -> None:
    assert (
        scraper._extract_match_id("https://www.hltv.org/matches/12345/a-vs-b") == 12345
    )
    assert scraper._extract_match_id("https://www.hltv.org/results") is None


def test_extract_matches_from_page_warns_and_skips_unparseable_date(
    scraper: ResultsScraper,
) -> None:
    scraper.driver = _FakePageDriver(
        """
        <html>
          <body>
            <div class="results-sublist">
              <div class="standard-headline">Results for not-a-date</div>
              <div class="result-con">
                <a href="/matches/111/a-vs-b"></a>
              </div>
            </div>
            <div class="results-sublist">
              <div class="standard-headline">Results for May 5th 2025</div>
              <div class="result-con">
                <a href="/matches/222/c-vs-d"></a>
              </div>
            </div>
          </body>
        </html>
        """
    )
    scraper.start_date = dt.date(2025, 1, 1)
    scraper.end_date = dt.date(2025, 12, 31)

    with mock.patch.object(results_scraper_module.logger, "warning") as warning_mock:
        matches, stop = scraper._extract_matches_from_page(
            "https://www.hltv.org/results?offset=0"
        )

    warning_mock.assert_called_once_with("Could not parse date: %s", "not-a-date")
    assert matches == ["https://www.hltv.org/matches/222/c-vs-d"]
    assert stop is False


def test_close_failure_raises_typed_error(scraper: ResultsScraper) -> None:
    def failing_quit() -> None:
        raise RuntimeError("browser already gone")

    scraper.driver.quit = failing_quit

    with pytest.raises(
        ResultsScrapeError, match="Failed to close results scraper driver."
    ) as exc_info:
        scraper.close()

    assert isinstance(exc_info.value.__cause__, RuntimeError)
