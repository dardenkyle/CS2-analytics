"""Fetches raw match HTML for downstream parsing."""

import time

from bs4 import BeautifulSoup
from seleniumbase import Driver

from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class MatchScraper:
    """
    Scrapes match pages and returns raw soup for later parsing.

    This class does NOT handle queue orchestration, parsing, or database insertion.
    """

    def __init__(self):
        self.driver = Driver(uc=True, headless=True)

    def __enter__(self) -> "MatchScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def fetch_soup(self, url: str) -> BeautifulSoup:
        """Loads a match page and returns its parsed HTML."""
        return self._fetch_soup(url)

    def _fetch_soup(self, url: str) -> BeautifulSoup:
        self.driver.get(url)
        time.sleep(3)
        return BeautifulSoup(self.driver.page_source, "html.parser")

    def close(self) -> None:
        """Closes the Selenium driver."""
        self.driver.quit()
        logger.info("Selenium driver closed.")
