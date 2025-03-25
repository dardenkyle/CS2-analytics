import re
import time
import random
import datetime as dt
from seleniumbase import Driver
from bs4 import BeautifulSoup
from utils.log_manager import get_logger

logger = get_logger(__name__)


class MatchScraper:
    """Scrapes match details, demo links, and map stats links from HLTV match pages."""

    def __init__(self):
        """Initializes the scraper with SeleniumBase driver."""
        self.driver = Driver(uc=True, headless=True)  # ✅ Undetected Chrome for stealth

    def fetch_match(self, match_url) -> BeautifulSoup:
        """Extracts match details, demo links, and map stats links from a single match page."""
        logger.info(f"🔄 Fetching match data from: {match_url}")

        print(f"Fetching page: {match_url}")
        self.driver.get(match_url)
        print("Page loaded successfully!")
        time.sleep(random.uniform(3, 5))  # ✅ Allow time for page load

        return BeautifulSoup(self.driver.page_source, "html.parser")

    def close(self) -> None:
        """Closes the Selenium driver."""
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")
