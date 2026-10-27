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


@dataclass(frozen=True)
class ResultsPage:
    """What one rendered listing page contained.

    `matches` are the (url, section date) pairs inside the window;
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

    Sections newer than `end_date` plus slack are skipped; the first section
    older than `start_date` minus slack ends the page with `reached_floor`.
    The slack exists because the source applies its date filter in its own
    zone while section headers render in the browser's (#215, ADR-0019).
    """
    soup = BeautifulSoup(page_source, "html.parser")
    result_count = len(soup.find_all("div", class_=RESULT_CLASS))
    matches: list[tuple[str, dt.date]] = []
    sections_seen = 0
    sections_parsed = 0

    for section in soup.find_all("div", class_=SECTION_CLASS):
        date_header = section.find("div", class_=SECTION_HEADER_CLASS)
        if not date_header:
            continue
        sections_seen += 1
        match_date = parse_section_date(date_header.text)
        if match_date is None:
            continue
        sections_parsed += 1

        if match_date > end_date + date_slack:
            continue
        if match_date < start_date - date_slack:
            logger.info(
                "Stopping at match date %s because it is out of range.", match_date
            )
            return ResultsPage(matches, result_count, reached_floor=True)

        for result in section.find_all("div", class_=RESULT_CLASS):
            a_tag = result.find("a", href=True)
            if not a_tag:
                continue
            matches.append((f"{link_origin}{a_tag['href']}", match_date))

    if sections_seen and not sections_parsed:
        logger.warning(
            "No date sections parsed on %s: %d section(s) skipped, so no "
            "matches were discovered from this page.",
            page_url,
            sections_seen,
        )

    return ResultsPage(matches, result_count)
