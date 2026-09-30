"""Fetches raw map HTML for downstream parsing."""

from bs4 import BeautifulSoup
from seleniumbase import Driver

from cs2_analytics.exceptions import MapScrapeError, SessionScrapeError
from cs2_analytics.scrapers.page_wait import (
    DEFAULT_CONTENT_WAIT_SECONDS,
    fetch_rendered_page,
)
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

REQUIRED_MAP_SELECTOR = "div.match-info-box"
MAP_PAGE_LABEL = "Map stats page"


class MapScraper:
    """
    Fetches map pages and returns soup objects for parsing.

    This scraper does NOT handle lifecycle-state orchestration, parsing, or
    persistence.
    """

    def __init__(
        self,
        content_wait_seconds: float = DEFAULT_CONTENT_WAIT_SECONDS,
    ) -> None:
        self.driver = Driver(uc=True, headless=True)
        self.content_wait_seconds = content_wait_seconds

    def __enter__(self) -> "MapScraper":  # noqa: UP037
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def fetch_soup(self, url: str) -> BeautifulSoup:
        """Loads a map page and returns its parsed HTML.

        A page that never renders the required selector, including the
        source's challenge interstitial, raises `SessionScrapeError` so the
        controller retries it with a fresh session.
        """
        try:
            page_source = fetch_rendered_page(
                self.driver,
                url,
                REQUIRED_MAP_SELECTOR,
                MAP_PAGE_LABEL,
                self.content_wait_seconds,
            )
            return BeautifulSoup(page_source, "html.parser")
        except SessionScrapeError:
            raise
        except Exception as e:
            raise SessionScrapeError(f"Failed to fetch map stats page: {url}") from e

    def close(self) -> None:
        """Closes the Selenium driver."""
        try:
            self.driver.quit()
            logger.info("Selenium driver closed.")
        except Exception as e:
            raise MapScrapeError("Failed to close map scraper driver.") from e
