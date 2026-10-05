"""Fetches raw match HTML for downstream parsing."""

from bs4 import BeautifulSoup
from seleniumbase import Driver

from cs2_analytics.exceptions import MatchScrapeError, SessionScrapeError
from cs2_analytics.scrapers.page_wait import (
    DEFAULT_CONTENT_WAIT_SECONDS,
    fetch_rendered_page,
)
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

# The page container, not a field the parser validates: a rendered page
# missing team names must reach the parser and fail there, not time out here.
REQUIRED_MATCH_SELECTOR = "div.match-page"
MATCH_PAGE_LABEL = "Match page"


class MatchScraper:
    """
    Scrapes match pages and returns raw soup for later parsing.

    This class does NOT handle lifecycle-state orchestration, parsing, or
    database insertion.
    """

    def __init__(
        self,
        content_wait_seconds: float = DEFAULT_CONTENT_WAIT_SECONDS,
    ) -> None:
        self.driver = Driver(uc=True, headless=True)
        self.content_wait_seconds = content_wait_seconds

    def __enter__(self) -> "MatchScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def fetch_soup(self, url: str) -> BeautifulSoup:
        """Loads a match page and returns its parsed HTML.

        A page that never renders the required selector, including the
        source's challenge interstitial, raises `SessionScrapeError` so the
        controller retries it with a fresh session instead of handing an
        empty page to the parser.
        """
        try:
            page_source = fetch_rendered_page(
                self.driver,
                url,
                REQUIRED_MATCH_SELECTOR,
                MATCH_PAGE_LABEL,
                self.content_wait_seconds,
            )
            return BeautifulSoup(page_source, "html.parser")
        except SessionScrapeError:
            raise
        except Exception as e:
            raise SessionScrapeError(f"Failed to fetch match page: {url}") from e

    def close(self) -> None:
        """Closes the Selenium driver."""
        try:
            self.driver.quit()
            logger.info("Selenium driver closed.")
        except Exception as e:
            raise MatchScrapeError("Failed to close match scraper driver.") from e
