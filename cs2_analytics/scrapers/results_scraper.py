"""Scrapes HLTV results pages and yields discovered match links.

Fetch-only by contract: this module performs no database or ingestion-state
writes. Discovered matches are yielded to the caller, and
ResultsStageService owns recording them.
"""

import datetime as dt
import random
import re
import time
from collections.abc import Iterator

from bs4 import BeautifulSoup
from seleniumbase import Driver

from cs2_analytics.config.config import END_DATE, HLTV_URL, MAX_MATCHES, START_DATE
from cs2_analytics.exceptions import ResultsScrapeError, SessionScrapeError
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class ResultsScraper:
    """
    Scrapes HLTV results pages and yields discovered match links.

    Designed to be used as a context manager to ensure the browser is closed.
    """

    def __init__(self) -> None:
        """Initializes the scraper with a SeleniumBase driver and config params."""
        self.driver = Driver(uc=True, headless=True)
        self.base_url = HLTV_URL
        self.start_date = dt.datetime.strptime(START_DATE, "%Y-%m-%d").date()
        self.end_date = dt.datetime.strptime(END_DATE, "%Y-%m-%d").date()

    def __enter__(self) -> "ResultsScraper":
        """Enables use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensures the Selenium driver is closed on exit."""
        self.close()

    def iter_match_batches(
        self, max_matches: int = MAX_MATCHES
    ) -> Iterator[list[tuple[int, str]]]:
        """
        Scrapes HLTV results pages and yields discovered matches per page.

        Args:
            max_matches (int): Maximum number of matches to discover.

        Yields:
            One list of (match_id, match_url) tuples per results page.
        """
        offset = 0
        total_discovered = 0

        while total_discovered < max_matches:
            page_url = f"{self.base_url}?offset={offset}&gameType=CS2"
            logger.info("Scraping page: %s", page_url)

            match_urls, stop = self._extract_matches_from_page(page_url)
            batch = []
            for full_url in match_urls:  # already starts with https://www.hltv.org
                if total_discovered >= max_matches:
                    break
                match_id = self._extract_match_id(full_url)
                if match_id:
                    batch.append((match_id, full_url))
                    total_discovered += 1

            if batch:
                yield batch

            if total_discovered >= max_matches or stop or not match_urls:
                break

            offset += 100
            time.sleep(random.uniform(1.0, 2.0))

        logger.info("Discovered %s matches total.", total_discovered)

    def _extract_matches_from_page(self, url: str) -> tuple[list[str], bool]:
        """
        Extracts match links from a results page.

        Args:
            url (str): Page URL to scrape.

        Returns:
            Tuple of (list of match URLs, whether to stop scraping)
        """
        try:
            self.driver.get(url)
            time.sleep(random.uniform(3, 5))
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
        except Exception as e:
            raise SessionScrapeError(f"Failed to fetch results page: {url}") from e

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
                logger.warning("Could not parse date: %s", raw_date)
                continue

            if match_date > self.end_date:
                continue
            if match_date < self.start_date:
                logger.info(
                    "Stopping at match date %s because it is out of range.", match_date
                )
                return matches, True

            for match in section.find_all("div", class_="result-con"):
                a_tag = match.find("a", href=True)
                if not a_tag:
                    continue
                full_url = f"https://www.hltv.org{a_tag['href']}"
                matches.append(full_url)

        return matches, stop_scraping

    def _extract_match_id(self, url: str) -> int | None:
        """
        Extracts numeric match ID from the match URL.

        Args:
            url (str): HLTV match URL.

        Returns:
            Match ID or None if not found.
        """
        match = re.search(r"/matches/(\d+)", url)
        return int(match.group(1)) if match else None

    def close(self) -> None:
        """Closes the SeleniumBase driver."""
        try:
            self.driver.quit()
            logger.info("Selenium driver closed.")
        except Exception as e:
            raise ResultsScrapeError("Failed to close results scraper driver.") from e
