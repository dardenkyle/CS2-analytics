"""Scrapes HLTV results page to extract match links and queues them."""

import time
import random
import datetime as dt
import re
from seleniumbase import Driver
from bs4 import BeautifulSoup
from config.config import HLTV_URL, START_DATE, END_DATE, MAX_MATCHES
from utils.log_manager import get_logger
from storage import match_queue

logger = get_logger(__name__)


class ResultsScraper:
    """Scrapes HLTV results and queues match links into match_scrape_queue."""

    def __init__(self):
        """Initializes the scraper with a SeleniumBase driver and config params."""
        self.driver = Driver(uc=True, headless=True)
        self.base_url = HLTV_URL
        self.start_date = dt.datetime.strptime(START_DATE, "%Y-%m-%d").date()
        self.end_date = dt.datetime.strptime(END_DATE, "%Y-%m-%d").date()

    def run(self, max_matches: int = MAX_MATCHES) -> None:
        """
        Scrapes HLTV results and queues match links.

        Args:
            max_matches (int): Maximum number of matches to queue.
        """
        offset = 0
        total_queued = 0

        while total_queued < max_matches:
            page_url = f"{self.base_url}?offset={offset}"
            logger.info("🔄 Scraping page: %s", page_url)

            match_urls, stop = self._extract_matches_from_page(page_url)
            for url in match_urls:
                match_id = self._extract_match_id(url)
                if not match_id:
                    continue

                match_queue.queue(match_id, url, source="results_scraper")
                total_queued += 1

                if total_queued >= max_matches:
                    break

            if stop or len(match_urls) == 0:
                break

            offset += 100
            time.sleep(random.uniform(1.0, 2.0))  # ✅ Polite crawl delay

        logger.info("✅ Queued %s matches total.", total_queued)

    def _extract_matches_from_page(self, url: str) -> tuple[list[str], bool]:
        """
        Extracts match links from a results page.

        Args:
            url (str): Page URL to scrape.

        Returns:
            Tuple of (list of match URLs, whether to stop scraping)
        """
        self.driver.get(url)
        time.sleep(random.uniform(3, 5))

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        matches = []
        stop_scraping = False

        for section in soup.find_all("div", class_="results-sublist"):
            date_header = section.find("div", class_="standard-headline")
            if not date_header:
                continue

            raw_date = re.sub(
                r"(st|nd|rd|th)", "", date_header.text.replace("Results for ", "")
            )
            try:
                match_date = dt.datetime.strptime(raw_date.strip(), "%B %d %Y").date()
            except ValueError:
                logger.warning("❌ Could not parse date: %s", raw_date)
                continue

            if match_date > self.end_date:
                continue
            if match_date < self.start_date:
                logger.info("⏹️ Stopping at match date %s — out of range.", match_date)
                return matches, True

            for match in section.find_all("div", class_="result-con"):
                a_tag = match.find("a", href=True)
                if not a_tag:
                    continue
                full_url = f"https://www.hltv.org{a_tag['href']}"
                matches.append(full_url)

        return matches, stop_scraping

    def _extract_match_id(self, url: str) -> str:
        """
        Extracts numeric match ID from the match URL.

        Args:
            url (str): HLTV match URL.

        Returns:
            str: Match ID or "" if not found.
        """
        match = re.search(r"/matches/(\d+)", url)
        return match.group(1) if match else ""

    def close(self):
        """Closes the SeleniumBase driver."""
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")
