"""Fetches and returns raw match HTML for queued match URLs.

Args:
    limit (int): Number of matches to fetch.

Returns:
    List of (soup, match_id, match_url) for downstream parsing.
"""

import time
from seleniumbase import Driver
from bs4 import BeautifulSoup
from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class MatchScraper:
    """
    Scrapes match pages from match_scrape_queue and returns raw soup for later parsing.

    This class does NOT handle parsing or database insertion.
    """

    def __init__(self):
        self.driver = Driver(uc=True, headless=True)

    def __enter__(self) -> "MatchScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def run(self, limit: int = 25) -> list[tuple[BeautifulSoup, str, str]]:
        """
        Fetches match pages and returns raw soup content.

        Returns:
            List of (soup, match_id, match_url) tuples for downstream parsing.
        """
        matches = match_queue.fetch(limit=limit)
        result = []

        for match_id, match_url in matches:
            try:
                logger.info("🔄 Fetching match %s", match_url)
                soup = self._fetch_soup(match_url)
                result.append((soup, match_id, match_url))
                time.sleep(1.0)
            except Exception as e:
                logger.error("❌ Failed to fetch %s: %s", match_url, e)
                match_queue.mark_failed(match_id, str(e)[:500])

        return result

    def _fetch_soup(self, url: str) -> BeautifulSoup:
        self.driver.get(url)
        time.sleep(3)
        return BeautifulSoup(self.driver.page_source, "html.parser")

    def close(self) -> None:
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")
