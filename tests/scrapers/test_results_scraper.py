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


_PAGE_DATE = dt.date(2026, 5, 1)


def _page(urls: list[str], stop: bool) -> tuple[list[tuple[str, dt.date]], bool]:
    return [(url, _PAGE_DATE) for url in urls], stop


# Explicit run-parameter window for iter_match_batches calls (ADR-0015).
_WINDOW = {"start_date": dt.date(2025, 1, 1), "end_date": dt.date(2026, 12, 31)}


def _full_pages(scraper: ResultsScraper) -> None:
    """Mocked page extracts carry no DOM count; treat every page as full."""
    scraper.last_page_result_count = ResultsScraper.PAGE_SIZE


def test_iter_match_batches_yields_page_batches_with_ids(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    _full_pages(scraper)
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
    _full_pages(scraper)
    calls = 0

    def fake_extract(_url: str) -> tuple[list[tuple[str, dt.date]], bool]:
        nonlocal calls
        calls += 1
        return [(f"https://www.hltv.org/matches/{calls}00/x-vs-y", _PAGE_DATE)], False

    monkeypatch.setattr(scraper, "_extract_matches_from_page", fake_extract)

    batches = list(scraper.iter_match_batches(max_matches=2, **_WINDOW))

    assert len(batches) == 2
    assert calls == 2
    assert scraper.stop_reason == ResultsScraper.STOP_BUDGET


def test_iter_match_batches_caps_within_a_page(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    _full_pages(scraper)
    urls = [
        (f"https://www.hltv.org/matches/{n}/x-vs-y", _PAGE_DATE)
        for n in (101, 102, 103)
    ]
    calls = 0

    def fake_extract(_url: str) -> tuple[list[tuple[str, dt.date]], bool]:
        nonlocal calls
        calls += 1
        return urls, False

    monkeypatch.setattr(scraper, "_extract_matches_from_page", fake_extract)

    batches = list(scraper.iter_match_batches(max_matches=2, **_WINDOW))

    assert batches == [
        [
            (101, "https://www.hltv.org/matches/101/x-vs-y", _PAGE_DATE),
            (102, "https://www.hltv.org/matches/102/x-vs-y", _PAGE_DATE),
        ]
    ]
    assert calls == 1


def test_iter_match_batches_without_a_cap_reads_until_the_page_is_empty(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    _full_pages(scraper)
    """The incremental day-walk passes no cap; the window bounds it (#231)."""
    def _urls(first: int, last: int) -> list[str]:
        return [f"https://www.hltv.org/matches/{i}/x" for i in range(first, last + 1)]

    pages = iter([_page(_urls(1, 100), False), _page(_urls(101, 130), False), ([], False)])
    monkeypatch.setattr(scraper, "_extract_matches_from_page", lambda _url: next(pages))

    batches = list(scraper.iter_match_batches(max_matches=None, **_WINDOW))

    assert [len(batch) for batch in batches] == [100, 30]
    assert scraper.stop_reason == ResultsScraper.STOP_EMPTY_PAGE


def test_iter_match_batches_stops_on_empty_page(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    _full_pages(scraper)
    monkeypatch.setattr(scraper, "_extract_matches_from_page", lambda _url: ([], False))

    assert list(scraper.iter_match_batches(max_matches=10, **_WINDOW)) == []
    assert scraper.stop_reason == ResultsScraper.STOP_EMPTY_PAGE


def test_iter_match_batches_applies_window_parameters(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    _full_pages(scraper)
    monkeypatch.setattr(scraper, "_extract_matches_from_page", lambda _url: ([], False))

    list(
        scraper.iter_match_batches(
            max_matches=1,
            start_date=dt.date(2025, 3, 1),
            end_date=dt.date(2025, 4, 1),
        )
    )

    assert scraper.start_date == dt.date(2025, 3, 1)
    assert scraper.end_date == dt.date(2025, 4, 1)


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
    assert matches == [
        ("https://www.hltv.org/matches/222/c-vs-d", dt.date(2025, 5, 5))
    ]
    assert stop is False


_BOUNDARY_PAGE = """
<html>
  <body>
    <div class="results-sublist">
      <div class="standard-headline">Results for October 27th 2026</div>
      <div class="result-con"><a href="/matches/333/after"></a></div>
    </div>
    <div class="results-sublist">
      <div class="standard-headline">Results for October 26th 2026</div>
      <div class="result-con"><a href="/matches/222/inside"></a></div>
    </div>
    <div class="results-sublist">
      <div class="standard-headline">Results for October 25th 2026</div>
      <div class="result-con"><a href="/matches/111/before"></a></div>
    </div>
    <div class="results-sublist">
      <div class="standard-headline">Results for October 24th 2026</div>
      <div class="result-con"><a href="/matches/000/far"></a></div>
    </div>
  </body>
</html>
"""


def test_source_filtered_window_keeps_sections_one_day_either_side(
    scraper: ResultsScraper,
) -> None:
    """The source filters in its own zone and renders headers in the browser's (#215)."""
    scraper.driver = _FakePageDriver(_BOUNDARY_PAGE)

    batches = list(
        scraper.iter_match_batches(
            max_matches=None,
            start_date=dt.date(2026, 10, 26),
            end_date=dt.date(2026, 10, 26),
            use_source_date_filter=True,
        )
    )

    assert [[url for _, url, _ in batch] for batch in batches] == [
        [
            "https://www.hltv.org/matches/333/after",
            "https://www.hltv.org/matches/222/inside",
            "https://www.hltv.org/matches/111/before",
        ]
    ]
    assert scraper.stop_reason == ResultsScraper.STOP_WINDOW_FLOOR


def test_a_short_page_ends_the_scan_without_requesting_the_next_page(
    scraper: ResultsScraper,
) -> None:
    """A filtered day fits on one page; the slack must not cost a second request."""
    scraper.driver = _FakePageDriver(_BOUNDARY_PAGE)

    batches = list(
        scraper.iter_match_batches(
            max_matches=None,
            start_date=dt.date(2026, 10, 25),
            end_date=dt.date(2026, 10, 26),
            use_source_date_filter=True,
        )
    )

    assert len(batches) == 1
    assert scraper.driver.loaded_urls == [
        "https://www.hltv.org/results?offset=0&gameType=CS2"
        "&startDate=2026-10-25&endDate=2026-10-26"
    ]
    assert scraper.stop_reason == ResultsScraper.STOP_EMPTY_PAGE


def test_unfiltered_window_still_stops_at_the_first_out_of_range_section(
    scraper: ResultsScraper,
) -> None:
    scraper.driver = _FakePageDriver(_BOUNDARY_PAGE)

    batches = list(
        scraper.iter_match_batches(
            max_matches=None,
            start_date=dt.date(2026, 10, 26),
            end_date=dt.date(2026, 10, 26),
        )
    )

    assert [[url for _, url, _ in batch] for batch in batches] == [
        ["https://www.hltv.org/matches/222/inside"]
    ]
    assert scraper.stop_reason == ResultsScraper.STOP_WINDOW_FLOOR


MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


@pytest.mark.parametrize("month_name", MONTH_NAMES)
def test_extract_matches_from_page_parses_ordinal_dates_for_every_month(
    scraper: ResultsScraper, month_name: str
) -> None:
    # Regression: an unanchored ordinal strip turned "August 31st 2026" into
    # "Augu 31 2026" and silently dropped every August section.
    scraper.driver = _FakePageDriver(
        f"""
        <html>
          <body>
            <div class="results-sublist">
              <div class="standard-headline">Results for {month_name} 3rd 2026</div>
              <div class="result-con">
                <a href="/matches/333/e-vs-f"></a>
              </div>
            </div>
          </body>
        </html>
        """
    )
    scraper.start_date = dt.date(2026, 1, 1)
    scraper.end_date = dt.date(2026, 12, 31)

    with mock.patch.object(results_scraper_module.logger, "warning") as warning_mock:
        matches, stop = scraper._extract_matches_from_page(
            "https://www.hltv.org/results?offset=0"
        )

    warning_mock.assert_not_called()
    assert [url for url, _date in matches] == [
        "https://www.hltv.org/matches/333/e-vs-f"
    ]
    assert all(date.year == 2026 and date.day == 3 for _url, date in matches)
    assert stop is False


def test_extract_matches_from_page_parses_observed_august_headers(
    scraper: ResultsScraper,
) -> None:
    scraper.driver = _FakePageDriver(
        """
        <html>
          <body>
            <div class="results-sublist">
              <div class="standard-headline">Results for August 31st 2026</div>
              <div class="result-con"><a href="/matches/1/a-vs-b"></a></div>
            </div>
            <div class="results-sublist">
              <div class="standard-headline">Results for August 22nd 2026</div>
              <div class="result-con"><a href="/matches/2/c-vs-d"></a></div>
            </div>
            <div class="results-sublist">
              <div class="standard-headline">Results for August 1st 2026</div>
              <div class="result-con"><a href="/matches/3/e-vs-f"></a></div>
            </div>
          </body>
        </html>
        """
    )
    scraper.start_date = dt.date(2026, 8, 1)
    scraper.end_date = dt.date(2026, 8, 31)

    matches, stop = scraper._extract_matches_from_page(
        "https://www.hltv.org/results?offset=0"
    )

    assert [url.rsplit("/", 2)[1] for url, _date in matches] == ["1", "2", "3"]
    assert [date.day for _url, date in matches] == [31, 22, 1]
    assert stop is False


def test_extract_matches_from_page_warns_when_no_sections_parse(
    scraper: ResultsScraper,
) -> None:
    scraper.driver = _FakePageDriver(
        """
        <html>
          <body>
            <div class="results-sublist">
              <div class="standard-headline">Results for not-a-date</div>
              <div class="result-con"><a href="/matches/1/a-vs-b"></a></div>
            </div>
            <div class="results-sublist">
              <div class="standard-headline">Results for also-not-a-date</div>
              <div class="result-con"><a href="/matches/2/c-vs-d"></a></div>
            </div>
          </body>
        </html>
        """
    )
    scraper.start_date = dt.date(2026, 1, 1)
    scraper.end_date = dt.date(2026, 12, 31)

    with mock.patch.object(results_scraper_module.logger, "warning") as warning_mock:
        matches, stop = scraper._extract_matches_from_page(
            "https://www.hltv.org/results?offset=0"
        )

    assert matches == []
    assert stop is False
    summary_calls = [
        call for call in warning_mock.call_args_list
        if call.args and str(call.args[0]).startswith("No date sections parsed")
    ]
    assert len(summary_calls) == 1
    assert summary_calls[0].args[2] == 2


def test_close_failure_raises_typed_error(scraper: ResultsScraper) -> None:
    def failing_quit() -> None:
        raise RuntimeError("browser already gone")

    scraper.driver.quit = failing_quit

    with pytest.raises(
        ResultsScrapeError, match="Failed to close results scraper driver."
    ) as exc_info:
        scraper.close()

    assert isinstance(exc_info.value.__cause__, RuntimeError)
