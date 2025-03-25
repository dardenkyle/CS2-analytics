import time
import random
import datetime as dt
from seleniumbase import Driver
from bs4 import BeautifulSoup
from config.config import HLTV_URL, START_DATE, END_DATE, MAX_MATCHES
from utils.log_manager import get_logger

logger = get_logger(__name__)


class ResultsScraper:
    """Scrapes HLTV results page to extract match links."""

    def __init__(self):
        """Initializes the scraper with a SeleniumBase driver."""
        self.driver = Driver(uc=True, headless=True)  # ✅ Uses Undetected Chrome Driver
        self.base_url = HLTV_URL
        self.match_links = []
        self.start_date = dt.datetime.strptime(START_DATE, "%Y-%m-%d").date()
        self.end_date = dt.datetime.strptime(END_DATE, "%Y-%m-%d").date()

    def fetch_results(self, max_matches=MAX_MATCHES) -> list[str]:
        """Scrapes match links from the results page."""
        offset = 0

        while len(self.match_links) < max_matches:
            page_url = f"{self.base_url}?offset={offset}"
            logger.info(f"🔄 Scraping: {page_url}")

            new_matches, stop_scraping = self._extract_matches_from_page(page_url)
            self.match_links.extend(new_matches)

            if stop_scraping or len(new_matches) < 0:
                break  # ✅ Stop if no more matches or reached date limit       #### Issue with this causing fetch_results to return empty list with len(new_matches) == 0

            offset += 100  # ✅ Move to next results page

        logger.info(
            f"✅ Found {len(self.match_links)} matches from {self.start_date} to {self.end_date}."
        )
        return self.match_links

    def _extract_matches_from_page(self, url):
        """Extracts match data from a given HLTV results page."""
        self.driver.get(url)
        time.sleep(random.uniform(3, 5))  # ✅ Allow page to load

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        matches = []
        stop_scraping = False

        results_sublist = soup.find_all("div", class_="results-sublist")

        for section in results_sublist:
            date_header = section.find("div", class_="standard-headline")

            if date_header:
                raw_date_text = (
                    date_header.text.replace("Results for ", "")
                    .replace("st", "")
                    .replace("nd", "")
                    .replace("rd", "")
                    .replace("th", "")
                )

                try:
                    match_date = dt.datetime.strptime(raw_date_text, "%B %d %Y").date()
                except ValueError:
                    logger.warning(f"❌ Could not parse date: {raw_date_text}")
                    continue

                if match_date > self.end_date:
                    continue  # ✅ Skip future matches

                if match_date < self.start_date:
                    logger.info(
                        f"⏩ Match date {match_date} is too old, stopping scraping."
                    )
                    return matches, True  # ✅ Stop if we reached old dates

                # ✅ Extract match links
                match_containers = section.find_all("div", class_="result-con")

                for match in match_containers:
                    if len(matches) >= 50:  # ✅ Stop when reaching max_matches
                        logger.info(f"✅ Reached max matches. Stopping scraping.")
                        return matches, True

                    match_link_tag = match.find("a", href=True)
                    if not match_link_tag:
                        continue

                    match_url = f"https://www.hltv.org{match_link_tag['href']}"
                    matches.append(match_url)

        return matches, stop_scraping

    def close(self):
        """Closes the Selenium driver."""
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")
