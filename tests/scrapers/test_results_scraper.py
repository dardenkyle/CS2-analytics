"""Tests for the fetch-only results scraper.

Page contents are the parser's concern (`tests/parsers/test_results_parser.py`);
these tests cover pagination, stop reasons, and the required-selector wait.
"""

import datetime as dt

import pytest

from cs2_analytics.exceptions import ResultsScrapeError, SessionScrapeError
from cs2_analytics.parsers.results_parser import ResultsPage
from cs2_analytics.scrapers import page_wait as page_wait_module
from cs2_analytics.scrapers import results_scraper as results_scraper_module
from cs2_analytics.scrapers.results_scraper import ResultsScraper
from tests.scrapers.page_fakes import FakeDriver, FakePollingWait


class _QuitOnlyDriver:
    def __init__(self, *args, **kwargs) -> None:
        self.quit_called = False

    def quit(self) -> None:
        self.quit_called = True


@pytest.fixture
def scraper(monkeypatch: pytest.MonkeyPatch) -> ResultsScraper:
    monkeypatch.setattr(results_scraper_module, "Driver", _QuitOnlyDriver)
    monkeypatch.setattr(
        results_scraper_module.time, "sleep", lambda *_args, **_kwargs: None
    )
    return ResultsScraper()


def _build_scraper(monkeypatch: pytest.MonkeyPatch, driver: FakeDriver) -> ResultsScraper:
    """A scraper over the shared fake driver so the selector wait is exercised."""
    monkeypatch.setattr(results_scraper_module, "Driver", lambda **_kwargs: driver)
    monkeypatch.setattr(page_wait_module, "WebDriverWait", FakePollingWait)
    monkeypatch.setattr(
        results_scraper_module.time, "sleep", lambda *_args, **_kwargs: None
    )
    return ResultsScraper(content_wait_seconds=0.1)


_PAGE_DATE = dt.date(2026, 5, 1)
# Explicit run-parameter window for iter_match_batches calls (ADR-0015).
_WINDOW = {"start_date": dt.date(2025, 1, 1), "end_date": dt.date(2026, 12, 31)}


def _page(urls: list[str], reached_floor: bool, *, full: bool = True) -> ResultsPage:
    """A parsed page; `full` makes it read as a complete 100-result page."""
    return ResultsPage(
        matches=[(url, _PAGE_DATE) for url in urls],
        result_count=ResultsScraper.PAGE_SIZE if full else len(urls),
        reached_floor=reached_floor,
    )


def _urls(first: int, last: int) -> list[str]:
    return [f"https://www.hltv.org/matches/{i}/x" for i in range(first, last + 1)]


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
                reached_floor=False,
            ),
            _page(["https://www.hltv.org/matches/333/e-vs-f"], reached_floor=True),
        ]
    )
    monkeypatch.setattr(scraper, "_fetch_page", lambda _url: next(pages))

    batches = list(scraper.iter_match_batches(max_matches=50, **_WINDOW))

    assert batches == [
        [
            (111, "https://www.hltv.org/matches/111/a-vs-b", _PAGE_DATE),
            (222, "https://www.hltv.org/matches/222/c-vs-d", _PAGE_DATE),
        ],
        [(333, "https://www.hltv.org/matches/333/e-vs-f", _PAGE_DATE)],
    ]
    assert scraper.stop_reason == ResultsScraper.STOP_WINDOW_FLOOR


def test_iter_match_batches_stops_at_max_matches(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fake_fetch(_url: str) -> ResultsPage:
        nonlocal calls
        calls += 1
        return _page([f"https://www.hltv.org/matches/{calls}00/x-vs-y"], False)

    monkeypatch.setattr(scraper, "_fetch_page", fake_fetch)

    batches = list(scraper.iter_match_batches(max_matches=2, **_WINDOW))

    assert len(batches) == 2
    assert calls == 2
    assert scraper.stop_reason == ResultsScraper.STOP_BUDGET


def test_iter_match_batches_caps_within_a_page(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fake_fetch(_url: str) -> ResultsPage:
        nonlocal calls
        calls += 1
        return _page(_urls(1, 3), False)

    monkeypatch.setattr(scraper, "_fetch_page", fake_fetch)

    batches = list(scraper.iter_match_batches(max_matches=2, **_WINDOW))

    assert batches == [
        [
            (1, "https://www.hltv.org/matches/1/x", _PAGE_DATE),
            (2, "https://www.hltv.org/matches/2/x", _PAGE_DATE),
        ]
    ]
    assert calls == 1
    assert scraper.stop_reason == ResultsScraper.STOP_BUDGET


def test_iter_match_batches_without_a_cap_reads_until_the_page_is_empty(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The incremental day-walk passes no cap; the window bounds it (#231)."""
    pages = iter(
        [_page(_urls(1, 100), False), _page(_urls(101, 130), False), _page([], False)]
    )
    monkeypatch.setattr(scraper, "_fetch_page", lambda _url: next(pages))

    batches = list(scraper.iter_match_batches(max_matches=None, **_WINDOW))

    assert [len(batch) for batch in batches] == [100, 30]
    assert scraper.stop_reason == ResultsScraper.STOP_EMPTY_PAGE


def test_iter_match_batches_stops_on_empty_page(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scraper, "_fetch_page", lambda _url: _page([], False))

    assert list(scraper.iter_match_batches(max_matches=10, **_WINDOW)) == []
    assert scraper.stop_reason == ResultsScraper.STOP_EMPTY_PAGE


def test_a_short_page_ends_the_scan_without_requesting_the_next_page(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A filtered day fits on one page; the slack must not cost a second request."""
    requested: list[str] = []

    def fake_fetch(url: str) -> ResultsPage:
        requested.append(url)
        return _page(_urls(1, 3), False, full=False)

    monkeypatch.setattr(scraper, "_fetch_page", fake_fetch)

    batches = list(
        scraper.iter_match_batches(
            max_matches=None,
            start_date=dt.date(2026, 10, 25),
            end_date=dt.date(2026, 10, 26),
            use_source_date_filter=True,
        )
    )

    assert len(batches) == 1
    assert requested == [
        "https://www.hltv.org/results?offset=0&gameType=CS2"
        "&startDate=2026-10-25&endDate=2026-10-26"
    ]
    assert scraper.stop_reason == ResultsScraper.STOP_EMPTY_PAGE


def test_iter_match_batches_applies_window_and_slack(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scraper, "_fetch_page", lambda _url: _page([], False))

    list(
        scraper.iter_match_batches(
            max_matches=1,
            start_date=dt.date(2025, 3, 1),
            end_date=dt.date(2025, 4, 1),
        )
    )
    assert scraper.start_date == dt.date(2025, 3, 1)
    assert scraper.end_date == dt.date(2025, 4, 1)
    assert scraper.date_slack == dt.timedelta(0)

    list(
        scraper.iter_match_batches(
            max_matches=1,
            start_date=dt.date(2025, 3, 1),
            end_date=dt.date(2025, 4, 1),
            use_source_date_filter=True,
        )
    )
    assert scraper.date_slack == dt.timedelta(days=1)


def test_rendered_empty_listing_is_an_empty_slice_not_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A page with the listing container and no results is a genuinely empty day (#230)."""
    driver = FakeDriver('<html><body><div class="results"></div></body></html>')
    scraper = _build_scraper(monkeypatch, driver)

    batches = list(
        scraper.iter_match_batches(
            max_matches=None,
            start_date=dt.date(2030, 1, 1),
            end_date=dt.date(2030, 1, 1),
            use_source_date_filter=True,
        )
    )

    assert batches == []
    assert scraper.stop_reason == ResultsScraper.STOP_EMPTY_PAGE
    assert driver.find_calls == [
        ("css selector", results_scraper_module.REQUIRED_RESULTS_SELECTOR)
    ]


def test_unrendered_listing_raises_the_retryable_session_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The challenge interstitial must not read as an empty slice (#230)."""
    driver = FakeDriver(
        "<html><head><title>Just a moment...</title></head>"
        "<body>Checking your browser before accessing the site.</body></html>",
        renders_after_polls=None,
    )
    scraper = _build_scraper(monkeypatch, driver)

    with pytest.raises(SessionScrapeError, match="blocked or challenged"):
        list(
            scraper.iter_match_batches(
                max_matches=None,
                start_date=dt.date(2026, 10, 26),
                end_date=dt.date(2026, 10, 26),
                use_source_date_filter=True,
            )
        )


def test_blank_render_without_markers_is_also_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver("<html><body></body></html>", renders_after_polls=None)
    scraper = _build_scraper(monkeypatch, driver)

    with pytest.raises(SessionScrapeError, match="missing required content"):
        list(scraper.iter_match_batches(max_matches=10, **_WINDOW))


def test_rendered_page_with_results_yields_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver(
        """
        <html><body><div class="results">
          <div class="results-sublist">
            <div class="standard-headline">Results for May 1st 2026</div>
            <div class="result-con"><a href="/matches/777/a-vs-b"></a></div>
          </div>
        </div></body></html>
        """
    )
    scraper = _build_scraper(monkeypatch, driver)

    batches = list(scraper.iter_match_batches(max_matches=10, **_WINDOW))

    assert batches == [[(777, "https://www.hltv.org/matches/777/a-vs-b", _PAGE_DATE)]]
    assert scraper.stop_reason == ResultsScraper.STOP_EMPTY_PAGE


def test_close_failure_raises_typed_error(scraper: ResultsScraper) -> None:
    def failing_quit() -> None:
        raise RuntimeError("browser already gone")

    scraper.driver.quit = failing_quit

    with pytest.raises(
        ResultsScrapeError, match="Failed to close results scraper driver."
    ) as exc_info:
        scraper.close()

    assert isinstance(exc_info.value.__cause__, RuntimeError)
