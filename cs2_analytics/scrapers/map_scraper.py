"""Fetches raw map HTML for downstream parsing."""

import time

from bs4 import BeautifulSoup
from seleniumbase import Driver

from cs2_analytics.exceptions import MapScrapeError, SessionScrapeError
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class MapScraper:
    """
    Fetches map pages and returns soup objects for parsing.

    This scraper does NOT handle queue orchestration, parsing, or persistence.
    """

    def __init__(self) -> None:
        self.driver = Driver(uc=True, headless=True)

    def __enter__(self) -> "MapScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def fetch_soup(self, url: str) -> BeautifulSoup:
        """Loads a map page and returns its parsed HTML."""
        try:
            self.driver.get(url)
            time.sleep(3.0)
            return BeautifulSoup(self.driver.page_source, "html.parser")
        except Exception as e:
            raise SessionScrapeError(f"Failed to fetch map stats page: {url}") from e

    def close(self) -> None:
        """Closes the Selenium driver."""
        try:
            self.driver.quit()
            logger.info("Selenium driver closed.")
        except Exception as e:
            raise MapScrapeError("Failed to close map scraper driver.") from e
