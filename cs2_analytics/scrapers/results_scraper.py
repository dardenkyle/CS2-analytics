"""Scrapes results listing pages and yields discovered match links.

Fetch-only by contract: this module loads pages, waits for them to render,
and paginates; `parsers.results_parser` decides what a page contains and
`ResultsStageService` owns recording the matches. No database or
ingestion-state writes happen here.
"""

import datetime as dt
import random
import time
from collections.abc import Generator
from urllib.parse import urlsplit

from seleniumbase import Driver

from cs2_analytics.config.config import SOURCE_URL
from cs2_analytics.exceptions import ResultsScrapeError, SessionScrapeError
from cs2_analytics.parsers.results_parser import (
    ResultsPage,
    extract_match_id,
    parse_results_page,
)
from cs2_analytics.scrapers.page_wait import (
    DEFAULT_CONTENT_WAIT_SECONDS,
    fetch_rendered_page,
)
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

# The listing container, present on a rendered page even when the requested
# date range has no results, so a rendered empty slice is distinguishable
# from the challenge interstitial or a blank render (#230). A page that never
# renders it raises the retryable session error through page_wait.
REQUIRED_RESULTS_SELECTOR = "div.results"
RESULTS_PAGE_LABEL = "Results page"


class ResultsScraper:
    """
    Scrapes results listing pages and yields discovered match links.

    Designed to be used as a context manager to ensure the browser is closed.
    """

    STOP_BUDGET = "budget_exhausted"
    STOP_WINDOW_FLOOR = "window_floor_reached"
    STOP_EMPTY_PAGE = "empty_page"

    # Days a section date may fall outside the requested window before the
    # client-side range check stops the scan, when the source's own date
    # filter is in use. The filter is applied in the source's zone while
    # section headers render in the browser's zone (#215), so a filtered
    # page legitimately carries sections dated one day either side of the
    # window; without slack those matches are dropped by every window and
    # never recorded. The slack still bounds a scan if the filter were ever
    # ignored.
    DATE_FILTER_SLACK_DAYS = 1

    # Results per listing page; the offset step and the last-page check
    # both rest on it. A page with fewer results is the last one, so the
    # scan ends without a request for the (empty) page after it.
    PAGE_SIZE = 100

    def __init__(
        self,
        content_wait_seconds: float = DEFAULT_CONTENT_WAIT_SECONDS,
    ) -> None:
        """Initializes the scraper with a SeleniumBase driver."""
        self.driver = Driver(uc=True, headless=True)
        self.base_url = SOURCE_URL
        parts = urlsplit(SOURCE_URL)
        self.link_origin = f"{parts.scheme}://{parts.netloc}"
        self.content_wait_seconds = content_wait_seconds
        self.stop_reason = self.STOP_EMPTY_PAGE
        self.start_date: dt.date | None = None
        self.end_date: dt.date | None = None
        self.date_slack = dt.timedelta(0)

    def __enter__(self) -> "ResultsScraper":
        """Enables use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Closes the browser on exit."""
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
                client-side date checks stay on as a safety net, with one
                day of slack for the source's zone.

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

            page = self._fetch_page(page_url)
            batch = []
            for full_url, match_date in page.matches:
                if max_matches is not None and total_discovered >= max_matches:
                    break
                match_id = extract_match_id(full_url)
                if match_id:
                    batch.append((match_id, full_url, match_date))
                    total_discovered += 1

            if batch:
                yield batch

            if max_matches is not None and total_discovered >= max_matches:
                self.stop_reason = self.STOP_BUDGET
                break
            if page.reached_floor:
                self.stop_reason = self.STOP_WINDOW_FLOOR
                break
            if not page.matches or page.result_count < self.PAGE_SIZE:
                self.stop_reason = self.STOP_EMPTY_PAGE
                break

            offset += self.PAGE_SIZE
            time.sleep(random.uniform(1.0, 2.0))

        logger.info(
            "Discovered %s matches total (stop_reason=%s).",
            total_discovered,
            self.stop_reason,
        )

    def _fetch_page(self, url: str) -> ResultsPage:
        """Loads one listing page, waits for it to render, and parses it.

        A page that never renders the listing container, including the
        source's challenge interstitial, raises `SessionScrapeError` so the
        controller retries with a fresh session instead of reading the page
        as an empty slice (#230).
        """
        assert self.start_date is not None and self.end_date is not None
        try:
            page_source = fetch_rendered_page(
                self.driver,
                url,
                REQUIRED_RESULTS_SELECTOR,
                RESULTS_PAGE_LABEL,
                self.content_wait_seconds,
            )
        except SessionScrapeError:
            raise
        except Exception as e:
            raise SessionScrapeError(f"Failed to fetch results page: {url}") from e
        return parse_results_page(
            page_source,
            start_date=self.start_date,
            end_date=self.end_date,
            date_slack=self.date_slack,
            page_url=url,
            link_origin=self.link_origin,
        )

    def close(self) -> None:
        """Closes the SeleniumBase driver."""
        try:
            self.driver.quit()
            logger.info("Selenium driver closed.")
        except Exception as e:
            raise ResultsScrapeError("Failed to close results scraper driver.") from e
