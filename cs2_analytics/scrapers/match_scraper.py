"""Fetches raw match HTML for downstream parsing."""

import time

from bs4 import BeautifulSoup
from seleniumbase import Driver

from cs2_analytics.exceptions import MatchScrapeError, SessionScrapeError
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class MatchScraper:
    """
    Scrapes match pages and returns raw soup for later parsing.

    This class does NOT handle lifecycle-state orchestration, parsing, or
    database insertion.
    """

    def __init__(self):
        self.driver = Driver(uc=True, headless=True)

    def __enter__(self) -> "MatchScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def fetch_soup(self, url: str) -> BeautifulSoup:
        """Loads a match page and returns its parsed HTML."""
        try:
            self.driver.get(url)
            time.sleep(3)
            return BeautifulSoup(self.driver.page_source, "html.parser")
        except Exception as e:
            raise SessionScrapeError(f"Failed to fetch match page: {url}") from e

    def close(self) -> None:
        """Closes the Selenium driver."""
        try:
            self.driver.quit()
            logger.info("Selenium driver closed.")
        except Exception as e:
            raise MatchScrapeError("Failed to close match scraper driver.") from e
