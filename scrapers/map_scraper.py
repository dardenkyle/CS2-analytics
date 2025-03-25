import time
import random
from bs4 import BeautifulSoup
from seleniumbase import Driver
from utils.log_manager import get_logger

logger = get_logger(__name__)


class MatchScraper:
    """
    Responsible for scraping the raw HTML from HLTV match and map pages.
    Returns parsed BeautifulSoup objects for further parsing.
    """

    def __init__(self):
        self.driver = Driver(uc=True, headless=True)

    def fetch_maps(self, url: str) -> BeautifulSoup:
        """Loads a given URL using SeleniumBase and returns a BeautifulSoup object."""
        try:
            logger.info(f"🌐 Fetching page: {url}")
            self.driver.get(url)
            time.sleep(
                random.uniform(3, 5)
            )  # Allow page to load and avoid rate limiting
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            logger.info(f"✅ Successfully parsed page: {url}")
            return soup
        except Exception as e:
            logger.error(f"❌ Error loading page {url}: {e}")
            return None

    def close(self):
        self.driver.quit()
        logger.info("🚪 Closed Selenium driver.")
