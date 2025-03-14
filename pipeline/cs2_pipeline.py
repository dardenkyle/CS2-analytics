from scrapers.results_scraper import ResultsScraper
from scrapers.match_scraper import MatchScraper
from storage.database import Database
from utils.log_manager import get_logger

class CS2AnalyticsPipeline:
    def __init__(self):
        """Initialize pipeline components."""
        self.logger = get_logger(self.__class__.__name__)
        self.results_scraper = ResultsScraper()
        self.match_scraper = MatchScraper()
        self.db = Database()

    def run(self):
        """Execute the full CS2 analytics pipeline."""
        self.logger.info("✅ Starting full CS2 pipeline.")

        # ✅ Step 1: Scrape Match Results
        self.logger.info("🔄 Scraping match results...")
        results = self.results_scraper.fetch_results()
        if not results:
            self.logger.warning("⚠️ No new matches found.")
            return

        # ✅ Step 2: Scrape Match Details (Includes Demo Links)
        self.logger.info("🔄 Scraping match details & demo links...")
        match_details = [self.match_scraper.fetch_match_data(url) for url in results]
        if not match_details:
            self.logger.warning("⚠️ No match details scraped.")
            return

        # ✅ Step 3: Store Data in the Database
        self.logger.info("💾 Storing match data in the database...")
        self.db.store_matches(match_details)
        self.logger.info("✅ Match data successfully stored.")

        self.logger.info("🚀 CS2 pipeline completed.")
