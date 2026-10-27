"""Parses a results listing page into dated match links.

Pure functions over page source: no fetching, no orchestration, no
persistence. `ResultsScraper` fetches and paginates; this module decides
what a fetched page contains so the listing logic is testable without a
driver (#230).
"""

import datetime as dt
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

SECTION_CLASS = "results-sublist"
SECTION_HEADER_CLASS = "standard-headline"
RESULT_CLASS = "result-con"
# Millisecond instant the source attaches to each result entry and groups
# the page by, in the browser's zone, when it renders the date headers.
ENTRY_UNIX_ATTR = "data-zonedgrouping-entry-unix"


@dataclass(frozen=True)
class ResultsPage:
    """What one rendered listing page contained.

    `matches` are the (url, match date) pairs inside the window, the date
    being each entry's own instant as a UTC calendar day (#215, ADR-0020);
    `result_count` is every result entry on the page regardless of date, so
    the scraper can tell a short last page from a full one; `reached_floor`
    is True when a section fell below the window floor (minus slack), which
    ends an offset-paged scan.
    """

    matches: list[tuple[str, dt.date]] = field(default_factory=list)
    result_count: int = 0
    reached_floor: bool = False


def parse_section_date(header_text: str) -> dt.date | None:
    """Parses a "Results for October 26th 2026" header; None when unparseable."""
    # Strip only day ordinals (31st, 2nd); an unanchored strip also removes
    # the "st" inside "August" and blanks the whole month.
    raw_date = re.sub(
        r"(?<=\d)(st|nd|rd|th)\b",
        "",
        header_text.replace("Results for ", ""),
    )
    try:
        return dt.datetime.strptime(raw_date.strip(), "%B %d %Y").date()
    except ValueError:
        logger.warning("Could not parse date: %s", raw_date)
        return None


def parse_entry_date(result) -> dt.date | None:
    """Returns the UTC calendar day of a result entry's own instant.

    None when the entry carries no instant or an unreadable one, in which
    case the caller falls back to the section header date.
    """
    raw_unix = result.get(ENTRY_UNIX_ATTR)
    if raw_unix is None:
        return None
    try:
        return dt.datetime.fromtimestamp(int(raw_unix) / 1000, tz=dt.UTC).date()
    except (TypeError, ValueError, OSError, OverflowError):
        logger.warning("Could not parse entry instant: %s", raw_unix)
        return None


def extract_match_id(url: str) -> int | None:
    """Returns the numeric match id from a match URL, or None."""
    match = re.search(r"/matches/(\d+)", url)
    return int(match.group(1)) if match else None


def parse_results_page(
    page_source: str,
    *,
    start_date: dt.date,
    end_date: dt.date,
    date_slack: dt.timedelta,
    page_url: str,
    link_origin: str,
) -> ResultsPage:
    """Extracts in-window match links with their section dates from a page.

    `link_origin` (scheme and host) is prefixed to the relative match links
    the listing carries.

    Each entry's date is the UTC day of its own instant, so the same page
    yields the same dates on every host; the section header, which the
    source renders in the browser's zone, is only the fallback for an entry
    without one (#215, ADR-0020). Entries newer than `end_date` plus slack
    are skipped; the first entry older than `start_date` minus slack ends
    the page with `reached_floor`. The slack exists because the source
    applies its date filter in its own zone (#215, ADR-0019).
    """
    soup = BeautifulSoup(page_source, "html.parser")
    result_count = len(soup.find_all("div", class_=RESULT_CLASS))
    matches: list[tuple[str, dt.date]] = []
    sections_seen = 0
    sections_dated = 0

    for section in soup.find_all("div", class_=SECTION_CLASS):
        date_header = section.find("div", class_=SECTION_HEADER_CLASS)
        if not date_header:
            continue
        sections_seen += 1
        section_date = parse_section_date(date_header.text)
        section_dated = section_date is not None

        for result in section.find_all("div", class_=RESULT_CLASS):
            a_tag = result.find("a", href=True)
            if not a_tag:
                continue
            match_date = parse_entry_date(result) or section_date
            if match_date is None:
                continue
            section_dated = True

            if match_date > end_date + date_slack:
                continue
            if match_date < start_date - date_slack:
                logger.info(
                    "Stopping at match date %s because it is out of range.", match_date
                )
                return ResultsPage(matches, result_count, reached_floor=True)
            matches.append((f"{link_origin}{a_tag['href']}", match_date))

        if section_dated:
            sections_dated += 1

    if sections_seen and not sections_dated:
        logger.warning(
            "No date sections parsed on %s: %d section(s) skipped, so no "
            "matches were discovered from this page.",
            page_url,
            sections_seen,
        )

    return ResultsPage(matches, result_count)
