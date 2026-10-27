"""Tests for the pure results listing parser (#230)."""

import datetime as dt
import time
from unittest import mock

import pytest

from cs2_analytics.parsers import results_parser as parser_module
from cs2_analytics.parsers.results_parser import (
    ResultsPage,
    extract_match_id,
    parse_results_page,
)

PAGE_URL = "https://www.hltv.org/results?offset=0"
NO_SLACK = dt.timedelta(0)
ONE_DAY = dt.timedelta(days=1)

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

_BOUNDARY_PAGE = """
<html>
  <body>
    <div class="results">
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
    </div>
  </body>
</html>
"""


def _parse(page: str, start: dt.date, end: dt.date, slack=NO_SLACK) -> ResultsPage:
    return parse_results_page(
        page,
        start_date=start,
        end_date=end,
        date_slack=slack,
        page_url=PAGE_URL,
        link_origin="https://www.hltv.org",
    )


def test_extract_match_id() -> None:
    assert extract_match_id("https://www.hltv.org/matches/12345/a-vs-b") == 12345
    assert extract_match_id("https://www.hltv.org/results") is None


def test_warns_and_skips_an_unparseable_section_date() -> None:
    page = """
    <html><body>
      <div class="results-sublist">
        <div class="standard-headline">Results for not-a-date</div>
        <div class="result-con"><a href="/matches/111/a-vs-b"></a></div>
      </div>
      <div class="results-sublist">
        <div class="standard-headline">Results for May 5th 2025</div>
        <div class="result-con"><a href="/matches/222/c-vs-d"></a></div>
      </div>
    </body></html>
    """

    with mock.patch.object(parser_module.logger, "warning") as warning_mock:
        result = _parse(page, dt.date(2025, 1, 1), dt.date(2025, 12, 31))

    warning_mock.assert_called_once_with("Could not parse date: %s", "not-a-date")
    assert result.matches == [
        ("https://www.hltv.org/matches/222/c-vs-d", dt.date(2025, 5, 5))
    ]
    assert result.result_count == 2
    assert result.reached_floor is False


@pytest.mark.parametrize("month_name", MONTH_NAMES)
def test_parses_ordinal_dates_for_every_month(month_name: str) -> None:
    # Regression: an unanchored ordinal strip turned "August 31st 2026" into
    # "Augu 31 2026" and silently dropped every August section.
    page = f"""
    <html><body>
      <div class="results-sublist">
        <div class="standard-headline">Results for {month_name} 3rd 2026</div>
        <div class="result-con"><a href="/matches/333/e-vs-f"></a></div>
      </div>
    </body></html>
    """

    with mock.patch.object(parser_module.logger, "warning") as warning_mock:
        result = _parse(page, dt.date(2026, 1, 1), dt.date(2026, 12, 31))

    warning_mock.assert_not_called()
    assert [url for url, _date in result.matches] == [
        "https://www.hltv.org/matches/333/e-vs-f"
    ]
    assert all(date.year == 2026 and date.day == 3 for _url, date in result.matches)


def test_parses_observed_august_headers() -> None:
    page = """
    <html><body>
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
    </body></html>
    """

    result = _parse(page, dt.date(2026, 8, 1), dt.date(2026, 8, 31))

    assert [url.rsplit("/", 2)[1] for url, _date in result.matches] == ["1", "2", "3"]
    assert [date.day for _url, date in result.matches] == [31, 22, 1]
    assert result.reached_floor is False


def test_warns_once_when_no_section_dates_parse() -> None:
    page = """
    <html><body>
      <div class="results-sublist">
        <div class="standard-headline">Results for not-a-date</div>
        <div class="result-con"><a href="/matches/1/a-vs-b"></a></div>
      </div>
      <div class="results-sublist">
        <div class="standard-headline">Results for also-not-a-date</div>
        <div class="result-con"><a href="/matches/2/c-vs-d"></a></div>
      </div>
    </body></html>
    """

    with mock.patch.object(parser_module.logger, "warning") as warning_mock:
        result = _parse(page, dt.date(2026, 1, 1), dt.date(2026, 12, 31))

    assert result.matches == []
    assert result.reached_floor is False
    summary_calls = [
        call
        for call in warning_mock.call_args_list
        if call.args and str(call.args[0]).startswith("No date sections parsed")
    ]
    assert len(summary_calls) == 1
    assert summary_calls[0].args[2] == 2


def test_source_filtered_window_keeps_sections_one_day_either_side() -> None:
    """The source filters in its own zone and renders headers in the browser's (#215)."""
    result = _parse(
        _BOUNDARY_PAGE, dt.date(2026, 10, 26), dt.date(2026, 10, 26), slack=ONE_DAY
    )

    assert [url for url, _ in result.matches] == [
        "https://www.hltv.org/matches/333/after",
        "https://www.hltv.org/matches/222/inside",
        "https://www.hltv.org/matches/111/before",
    ]
    assert result.reached_floor is True
    assert result.result_count == 4


def test_unfiltered_window_stops_at_the_first_out_of_range_section() -> None:
    result = _parse(_BOUNDARY_PAGE, dt.date(2026, 10, 26), dt.date(2026, 10, 26))

    assert [url for url, _ in result.matches] == [
        "https://www.hltv.org/matches/222/inside"
    ]
    assert result.reached_floor is True


def test_rendered_empty_listing_parses_as_no_matches() -> None:
    """A rendered page with the container and no sections is a genuinely empty slice."""
    page = '<html><body><div class="results"></div></body></html>'

    with mock.patch.object(parser_module.logger, "warning") as warning_mock:
        result = _parse(page, dt.date(2030, 1, 1), dt.date(2030, 1, 1), slack=ONE_DAY)

    warning_mock.assert_not_called()
    assert result == ResultsPage(matches=[], result_count=0, reached_floor=False)


_ENTRY_INSTANT_PAGE = """
<html><body>
  <div class="results">
    <div class="results-sublist">
      <div class="standard-headline">Results for October 26th 2026</div>
      <div class="result-con" data-zonedgrouping-entry-unix="1793076540000">
        <a href="/matches/444/after-midnight-utc"></a>
      </div>
      <div class="result-con" data-zonedgrouping-entry-unix="1793037600000">
        <a href="/matches/555/same-day"></a>
      </div>
      <div class="result-con"><a href="/matches/666/no-instant"></a></div>
    </div>
  </div>
</body></html>
"""


@pytest.fixture
def host_timezone(monkeypatch: pytest.MonkeyPatch):
    """Switches the process timezone for a test and restores it afterwards."""
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset is POSIX-only; the host zone cannot be switched here")

    def set_zone(zone: str) -> None:
        monkeypatch.setenv("TZ", zone)
        time.tzset()

    yield set_zone
    monkeypatch.undo()
    time.tzset()


def test_entry_instant_gives_the_utc_day_and_the_header_is_only_a_fallback() -> None:
    result = _parse(_ENTRY_INSTANT_PAGE, dt.date(2026, 10, 1), dt.date(2026, 10, 31))

    assert result.matches == [
        ("https://www.hltv.org/matches/444/after-midnight-utc", dt.date(2026, 10, 27)),
        ("https://www.hltv.org/matches/555/same-day", dt.date(2026, 10, 26)),
        ("https://www.hltv.org/matches/666/no-instant", dt.date(2026, 10, 26)),
    ]


def test_entry_dates_are_the_same_on_every_host(host_timezone) -> None:
    dates = []
    for zone in ("UTC", "America/Chicago", "Asia/Tokyo"):
        host_timezone(zone)
        result = _parse(_ENTRY_INSTANT_PAGE, dt.date(2026, 10, 1), dt.date(2026, 10, 31))
        dates.append([date for _, date in result.matches])

    assert dates[0] == dates[1] == dates[2]
    assert dates[0][0] == dt.date(2026, 10, 27)


def test_window_checks_use_the_entry_date_not_the_header() -> None:
    result = _parse(_ENTRY_INSTANT_PAGE, dt.date(2026, 10, 26), dt.date(2026, 10, 26))

    assert [url for url, _ in result.matches] == [
        "https://www.hltv.org/matches/555/same-day",
        "https://www.hltv.org/matches/666/no-instant",
    ]
    assert result.reached_floor is False


def test_unreadable_entry_instant_warns_and_falls_back_to_the_header() -> None:
    page = _ENTRY_INSTANT_PAGE.replace(
        'data-zonedgrouping-entry-unix="1793076540000"',
        'data-zonedgrouping-entry-unix="soon"',
    )

    with mock.patch.object(parser_module.logger, "warning") as warning_mock:
        result = _parse(page, dt.date(2026, 10, 1), dt.date(2026, 10, 31))

    warning_mock.assert_called_once_with("Could not parse entry instant: %s", "soon")
    assert result.matches[0] == (
        "https://www.hltv.org/matches/444/after-midnight-utc",
        dt.date(2026, 10, 26),
    )


def test_entries_with_instants_are_dated_even_when_the_header_is_not() -> None:
    page = _ENTRY_INSTANT_PAGE.replace("Results for October 26th 2026", "Results for ?")

    with mock.patch.object(parser_module.logger, "warning") as warning_mock:
        result = _parse(page, dt.date(2026, 10, 1), dt.date(2026, 10, 31))

    assert [url for url, _ in result.matches] == [
        "https://www.hltv.org/matches/444/after-midnight-utc",
        "https://www.hltv.org/matches/555/same-day",
    ]
    summary_calls = [
        call
        for call in warning_mock.call_args_list
        if call.args and str(call.args[0]).startswith("No date sections parsed")
    ]
    assert summary_calls == []
