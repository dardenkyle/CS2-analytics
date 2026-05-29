"""Fetches raw map HTML for downstream parsing."""

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver

from cs2_analytics.exceptions import MapScrapeError, SessionScrapeError
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

REQUIRED_MAP_SELECTOR = "div.match-info-box"
DEFAULT_CONTENT_WAIT_SECONDS = 10.0
PAGE_SNIPPET_LIMIT = 300
CHALLENGE_MARKERS = (
    "access denied",
    "captcha",
    "checking your browser",
    "cloudflare",
    "enable javascript",
    "just a moment",
    "verify you are human",
)


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

    def __enter__(self) -> MapScraper:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def fetch_soup(self, url: str) -> BeautifulSoup:
        """Loads a map page and returns its parsed HTML."""
        try:
            self.driver.get(url)
            self._wait_for_map_content(url)
            return BeautifulSoup(self.driver.page_source, "html.parser")
        except SessionScrapeError:
            raise
        except Exception as e:
            raise SessionScrapeError(f"Failed to fetch map stats page: {url}") from e

    def _wait_for_map_content(self, url: str) -> None:
        """Waits until the fetched page contains expected map stats content."""
        try:
            WebDriverWait(self.driver, self.content_wait_seconds).until(
                lambda driver: driver.find_element(
                    By.CSS_SELECTOR,
                    REQUIRED_MAP_SELECTOR,
                )
            )
        except TimeoutException as e:
            marker_flags = self._log_missing_map_content(url)
            challenge_markers = [
                marker for marker, is_present in marker_flags.items() if is_present
            ]
            if challenge_markers:
                marker_list = ", ".join(challenge_markers)
                raise SessionScrapeError(
                    "Map stats page appears blocked or challenged "
                    f"after {self.content_wait_seconds:g}s "
                    f"(markers: {marker_list}): {url}"
                ) from e
            raise SessionScrapeError(
                "Map stats page missing required content "
                f"after {self.content_wait_seconds:g}s: {url}"
            ) from e

    def _log_missing_map_content(self, requested_url: str) -> dict[str, bool]:
        page_source = self.driver.page_source or ""
        page_source_lower = page_source.lower()
        marker_flags = {
            marker.replace(" ", "_"): marker in page_source_lower
            for marker in CHALLENGE_MARKERS
        }
        snippet = " ".join(page_source.split())[:PAGE_SNIPPET_LIMIT]

        logger.warning(
            "Map stats page missing required selector=%s requested_url=%s "
            "current_url=%s title=%s page_source_length=%d marker_flags=%s "
            "page_snippet=%r",
            REQUIRED_MAP_SELECTOR,
            requested_url,
            getattr(self.driver, "current_url", None),
            getattr(self.driver, "title", None),
            len(page_source),
            marker_flags,
            snippet,
        )
        return marker_flags

    def close(self) -> None:
        """Closes the Selenium driver."""
        try:
            self.driver.quit()
            logger.info("Selenium driver closed.")
        except Exception as e:
            raise MapScrapeError("Failed to close map scraper driver.") from e
