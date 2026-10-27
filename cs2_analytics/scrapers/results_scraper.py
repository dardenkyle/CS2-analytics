"""Scrapes HLTV results pages and yields discovered match links.

Fetch-only by contract: this module performs no database or ingestion-state
writes. Discovered matches are yielded to the caller, and
ResultsStageService owns recording them.
"""

import datetime as dt
import random
import re
import time
from collections.abc import Generator

from bs4 import BeautifulSoup
from seleniumbase import Driver

from cs2_analytics.config.config import SOURCE_URL
from cs2_analytics.exceptions import ResultsScrapeError, SessionScrapeError
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class ResultsScraper:
    """
    Scrapes HLTV results pages and yields discovered match links.

    Designed to be used as a context manager to ensure the browser is closed.
    """

    # Why the last iter_match_batches call stopped (#121). The scraper
    # reports its own fetch-level stop cause; run-level semantics (for
    # example "up to date") belong to the controller.
    STOP_BUDGET = "budget_exhausted"
    STOP_WINDOW_FLOOR = "window_floor_reached"
    STOP_EMPTY_PAGE = "empty_page"

    # Results per listing page; the offset step and the last-page check
    # both rest on it. A page with fewer results is the last one, so the
    # scan ends without a request for the (empty) page after it.
    PAGE_SIZE = 100

    # Days a section date may fall outside the requested window before the
    # client-side range check stops the scan, when the source's own date
    # filter is in use. The filter is applied in the source's zone while
    # section headers render in the browser's zone (#215), so a filtered
    # page legitimately carries sections dated one day either side of the
    # window; without slack those matches are dropped by every window and
    # never recorded. The slack still bounds a scan if the filter were ever
    # ignored.
    DATE_FILTER_SLACK_DAYS = 1

    def __init__(self) -> None:
        """Initializes the scraper with a SeleniumBase driver."""
        self.driver = Driver(uc=True, headless=True)
        self.base_url = SOURCE_URL
        self.stop_reason = self.STOP_EMPTY_PAGE
        self.date_slack = dt.timedelta(0)
        self.last_page_result_count = 0

    def __enter__(self) -> "ResultsScraper":
        """Enables use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensures the Selenium driver is closed on exit."""
        self.close()

    def iter_match_batches(
        self,
        max_matches: int | None,
        start_date: dt.date,
        end_date: dt.date,
        use_source_date_filter: bool = False,
    ) -> Generator[list[tuple[int, str, dt.date]], None, None]:
        """
        Scrapes results pages and yields discovered matches per page.

        Run parameters are explicit per call (ADR-0015): the caller owns
        the discovery window and cap; the scraper holds no run defaults.
        After iteration finishes, `stop_reason` records why the scraper
        stopped (STOP_BUDGET, STOP_WINDOW_FLOOR, or STOP_EMPTY_PAGE) so
        the controller can report it (#121). STOP_EMPTY_PAGE also covers a
        page shorter than PAGE_SIZE, which is the last page of the listing.

        Args:
            max_matches (int | None): Maximum number of matches to
                discover, or None for no cap (the incremental day-walk
                is bounded by its date window instead, #231).
            start_date (dt.date): Window floor; discovery stops at older dates.
            end_date (dt.date): Window ceiling; newer dates are skipped.
            use_source_date_filter (bool): When True, the window is also
                passed to the results listing as date-range query
                parameters, so a backfill slice fetches only its chunk
                instead of paging from the newest results (#121). The
                client-side date checks stay on as a safety net.

        Yields:
            One list of (match_id, match_url, match_date) tuples per
            results page, where match_date is the parsed section date.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.date_slack = dt.timedelta(
            days=self.DATE_FILTER_SLACK_DAYS if use_source_date_filter else 0
        )
        self.stop_reason = self.STOP_BUDGET
        offset = 0
        total_discovered = 0

        while max_matches is None or total_discovered < max_matches:
            page_url = f"{self.base_url}?offset={offset}&gameType=CS2"
            if use_source_date_filter:
                page_url += f"&startDate={start_date}&endDate={end_date}"
            logger.info("Scraping page: %s", page_url)

            dated_urls, stop = self._extract_matches_from_page(page_url)
            batch = []
            for full_url, match_date in dated_urls:
                if max_matches is not None and total_discovered >= max_matches:
                    break
                match_id = self._extract_match_id(full_url)
                if match_id:
                    batch.append((match_id, full_url, match_date))
                    total_discovered += 1

            if batch:
                yield batch

            if max_matches is not None and total_discovered >= max_matches:
                self.stop_reason = self.STOP_BUDGET
                break
            if stop:
                self.stop_reason = self.STOP_WINDOW_FLOOR
                break
            if not dated_urls or self.last_page_result_count < self.PAGE_SIZE:
                self.stop_reason = self.STOP_EMPTY_PAGE
                break

            offset += self.PAGE_SIZE
            time.sleep(random.uniform(1.0, 2.0))

        logger.info(
            "Discovered %s matches total (stop_reason=%s).",
            total_discovered,
            self.stop_reason,
        )

    def _extract_matches_from_page(
        self, url: str
    ) -> tuple[list[tuple[str, dt.date]], bool]:
        """
        Extracts match links with their section dates from a results page.

        Args:
            url (str): Page URL to scrape.

        Returns:
            Tuple of (list of (match URL, section date) pairs, whether to
            stop scraping)
        """
        try:
            self.driver.get(url)
            time.sleep(random.uniform(3, 5))
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
        except Exception as e:
            raise SessionScrapeError(f"Failed to fetch results page: {url}") from e

        matches: list[tuple[str, dt.date]] = []
        stop_scraping = False
        sections_seen = 0
        sections_parsed = 0
        self.last_page_result_count = len(soup.find_all("div", class_="result-con"))

        for section in soup.find_all("div", class_="results-sublist"):
            date_header = section.find("div", class_="standard-headline")
            if not date_header:
                continue
            sections_seen += 1

            # Strip only day ordinals (31st, 2nd); an unanchored strip also
            # removes the "st" inside "August" and blanks the whole month.
            raw_date = re.sub(
                r"(?<=\d)(st|nd|rd|th)\b",
                "",
                date_header.text.replace("Results for ", ""),
            )
            try:
                match_date = dt.datetime.strptime(raw_date.strip(), "%B %d %Y").date()
            except ValueError:
                logger.warning("Could not parse date: %s", raw_date)
                continue
            sections_parsed += 1

            if match_date > self.end_date + self.date_slack:
                continue
            if match_date < self.start_date - self.date_slack:
                logger.info(
                    "Stopping at match date %s because it is out of range.", match_date
                )
                return matches, True

            for match in section.find_all("div", class_="result-con"):
                a_tag = match.find("a", href=True)
                if not a_tag:
                    continue
                full_url = f"https://www.hltv.org{a_tag['href']}"
                matches.append((full_url, match_date))

        if sections_seen and not sections_parsed:
            logger.warning(
                "No date sections parsed on %s: %d section(s) skipped, so no "
                "matches were discovered from this page.",
                url,
                sections_seen,
            )

        return matches, stop_scraping

    def _extract_match_id(self, url: str) -> int | None:
        """
        Extracts numeric match ID from the match URL.

        Args:
            url (str): HLTV match URL.

        Returns:
            Match ID or None if not found.
        """
        match = re.search(r"/matches/(\d+)", url)
        return int(match.group(1)) if match else None

    def close(self) -> None:
        """Closes the SeleniumBase driver."""
        try:
            self.driver.quit()
            logger.info("Selenium driver closed.")
        except Exception as e:
            raise ResultsScrapeError("Failed to close results scraper driver.") from e
