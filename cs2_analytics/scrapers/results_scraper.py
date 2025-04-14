"""Scrapes HLTV results page to extract match links and queues them."""

import time
import random
import datetime as dt
import re
from typing import List, Tuple
from seleniumbase import Driver
from bs4 import BeautifulSoup
from cs2_analytics.config.config import HLTV_URL, START_DATE, END_DATE, MAX_MATCHES
from cs2_analytics.utils.log_manager import get_logger
from cs2_analytics.utils.queue_helpers import chunk_and_queue
from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue

logger = get_logger(__name__)


class ResultsScraper:
    """
    Scrapes HLTV results and queues match links into match_scrape_queue.

    Designed to be used as a context manager to ensure the browser is closed.
    """

    def __init__(self) -> None:
        """Initializes the scraper with a SeleniumBase driver and config params."""
        self.driver = Driver(uc=True, headless=True)
        self.base_url = HLTV_URL
        self.queue = MatchScrapeQueue()
        self.source: str = "results_scraper"
        self.start_date = dt.datetime.strptime(START_DATE, "%Y-%m-%d").date()
        self.end_date = dt.datetime.strptime(END_DATE, "%Y-%m-%d").date()

    def __enter__(self) -> "ResultsScraper":
        """Enables use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensures the Selenium driver is closed on exit."""
        self.close()

    def run(self, max_matches: int = MAX_MATCHES) -> None:
        """
        Scrapes HLTV results and queues match links.

        Args:
            max_matches (int): Maximum number of matches to queue.
        """
        offset = 0
        total_queued = 0

        while total_queued < max_matches:
            page_url = f"{self.base_url}?offset={offset}&gameType=CS2"
            logger.info("🔄 Scraping page: %s", page_url)

            match_urls, stop = self._extract_matches_from_page(page_url)
            batch = []
            for full_url in match_urls:  # already starts with https://www.hltv.org
                match_id = self._extract_match_id(full_url)
                if match_id:
                    batch.append((match_id, full_url))
                    total_queued += 1

            chunk_and_queue(
                items=batch,
                queue_obj=self.queue,
                chunk_size=1000,
                source=self.source,
            )

            if stop or not match_urls:
                break

            offset += 100
            time.sleep(random.uniform(1.0, 2.0))  # Polite crawl delay

        logger.info("✅ Queued %s matches total.", total_queued)

    def _extract_matches_from_page(self, url: str) -> Tuple[List[str], bool]:
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

    def close(self) -> None:
        """Closes the SeleniumBase driver."""
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")


if __name__ == "__main__":
    with ResultsScraper() as scraper:
        scraper.run(max_matches=50)
