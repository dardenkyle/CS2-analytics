"""This module is responsible for scraping the raw HTML from HLTV map pages."""

import time
import random
from bs4 import BeautifulSoup
from seleniumbase import Driver
from utils.log_manager import get_logger

logger = get_logger(__name__)


class MapScraper:
    """
    Responsible for scraping the raw HTML from HLTV match and map pages.
    Returns parsed BeautifulSoup objects for further parsing.
    """

    def __init__(self):
        self.driver = Driver(uc=True, headless=True)

    def fetch_map(self, url: str) -> BeautifulSoup:
        """Loads a given URL using SeleniumBase and returns a BeautifulSoup object."""
        try:
            logger.info("Fetching page: %s", url)
            self.driver.get(url)
            time.sleep(
                random.uniform(10, 15)
            )  # Allow page to load and avoid rate limiting
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            logger.info("Successfully parsed page: %s", url)
            return soup
        except ConnectionError as e:
            logger.error("Error loading page %s: %s", url, e)
            return None

    def close(self):
        """Closes the Selenium driver."""
        self.driver.quit()
        logger.info("🚪 Closed Selenium driver.")
