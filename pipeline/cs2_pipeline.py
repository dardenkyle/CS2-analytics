from scrapers.results_scraper import ResultsScraper
from scrapers.match_scraper import MatchScraper
from storage.database import Database
from utils.log_manager import get_logger
from utils.initialize_db import initialize_database
import logging
from config.config import DEBUG_MODE

class CS2AnalyticsPipeline:
    def __init__(self) -> None:
        """Initialize pipeline components."""
        print("🚀 CS2AnalyticsPipeline Initialized!")  # ✅ Debug print
        self.logger = get_logger(self.__class__.__name__)
        print("✅ Logger initialized correctly!")
        
        # ✅ Explicitly set logging level
        self.logger.setLevel(logging.DEBUG)

        # ✅ Print the actual logger level
        print(f"🔍 Logger Level: {self.logger.level}")  # Should be 10 (DEBUG), 20 (INFO), etc.

        if not self.logger.hasHandlers():
            print("⚠️ No handlers found! Logs won't appear properly.")
        else:
            for handler in self.logger.handlers:
                print(f"🛠️ Handler: {handler}, Level: {handler.level}")

        print("🟡 Attempting to log a debug message now...")

        self.logger.debug("🔵 This is a DEBUG log (should appear).")
        self.logger.info("🟢 This is an INFO log (should appear).")
        self.logger.warning("🟡 This is a WARNING log (should appear).")
        self.logger.error("🔴 This is an ERROR log (should appear).")
        self.logger.info("✅ This is a DEBUG log from CS2AnalyticsPipeline.")
        print("🟢 This print statement should appear AFTER logging attempt.")
        
        
        
        self.results_scraper = ResultsScraper()
        self.match_scraper  = MatchScraper()
        self.db = Database()

    def run(self) -> None:
        """Execute the full CS2 analytics pipeline."""
        self.logger.info("✅ Starting full CS2 pipeline.")

        # if DEBUG_MODE:
        #     print("Initializing database for testing...")
        #     initialize_database()

        # ✅ Step 1: Scrape Match Results
        self.logger.info("🔄 Scraping match results...")
        results = self.results_scraper.fetch_results()
        print(results[0])
        print(len(results))
        if not results:
            print("no results found.. issue with fetch_results maybe...")
            self.logger.warning("⚠️ No new matches found.")
            return

        # ✅ Step 2: Scrape Match Details (Includes Demo Links)
        self.logger.info("🔄 Scraping match details & demo links...")
        print(len(results))
        print("Processing match URL")
        match_details = [self.match_scraper.fetch_match_data(url) for url in results]
        if not match_details:
            self.logger.warning("⚠️ No match details scraped.")
            return

        # ✅ Step 3: Store Data in the Database
        self.logger.info("💾 Storing match data in the database...")
        # ✅ Step 3: Store Data in the Database
        self.logger.info("💾 Storing match data in the database...")
        print("💾 Storing match data in the database...")
        print(f"📊 Match Data:\n{match_details}")  # Print before inserting
        self.db.store_matches(match_details)

        self.logger.info("✅ Match data successfully stored.")
        print("✅ Match data successfully stored.")  # Confirm if this prints

        self.logger.info("✅ Match data successfully stored.")

        self.logger.info("🚀 CS2 pipeline completed.")
