"""Scrapes HLTV map stats pages from the queue and returns soup for parsing."""

import time
from seleniumbase import Driver
from bs4 import BeautifulSoup
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class MapScraper:
    """
    Fetches map pages from `map_scrape_queue`, returning soup objects for parsing.

    This scraper does NOT handle parsing or saving to the database.
    Use it with `MapParser` after fetching soups.
    """

    def __init__(self) -> None:
        self.driver = Driver(uc=True, headless=True)

    def __enter__(self) -> "MapScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def run(self, limit: int = 25) -> list[tuple[BeautifulSoup, str, str]]:
        """
        Fetches queued map pages and returns soups for parsing.

        Args:
            limit (int): Maximum number of queued map pages to scrape.

        Returns:
            List of tuples: (soup, map_id, map_url)
        """
        queued = map_queue.fetch(limit=limit)
        results = []

        for map_id, map_url in queued:
            try:
                logger.info("🌍 Fetching map page: %s", map_url)
                soup = self._fetch_soup(map_url)
                results.append((soup, map_id, map_url))
                map_queue.mark_parsed(map_id)
                time.sleep(1.0)
            except Exception as e:
                logger.error("❌ Failed to fetch map %s: %s", map_url, e)
                map_queue.mark_failed(map_id, str(e)[:500])

        return results

    def _fetch_soup(self, url: str) -> BeautifulSoup:
        """Loads a map page and returns its parsed HTML."""
        self.driver.get(url)
        time.sleep(3.0)
        return BeautifulSoup(self.driver.page_source, "html.parser")

    def close(self) -> None:
        """Closes the Selenium driver."""
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")
