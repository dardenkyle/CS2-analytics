"""Controls the flow of the CS2 Analytics Pipeline."""

import logging

from bs4 import BeautifulSoup
from config.config import DEBUG_MODE
from models.match import Match
from models.player import Player
from parsers.map_parser import MapParser
from parsers.match_parser import MatchParser
from scrapers.match_scraper import MatchScraper
from scrapers.results_scraper import ResultsScraper
from storage.database import Database
from utils.initialize_db import initialize_database
from utils.log_manager import get_logger


class CS2AnalyticsPipeline:
    """Controls the flow of the CS2 Analytics Pipeline."""

    def __init__(self) -> None:
        """Initialize pipeline components."""
        print("🚀 CS2AnalyticsPipeline Initialized!")  # ✅ Debug print
        self.logger = get_logger(self.__class__.__name__)
        print("✅ Logger initialized correctly!")

        # ✅ Explicitly set logging level
        self.logger.setLevel(logging.DEBUG)

        # ✅ Print the actual logger level
        print(
            f"🔍 Logger Level: {self.logger.level}"
        )  # Should be 10 (DEBUG), 20 (INFO), etc.

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
        self.match_scraper = MatchScraper()
        self.db = Database()

    def run(self) -> None:
        """Execute the full CS2 analytics pipeline."""
        self.logger.info("✅ Starting full CS2 pipeline.")

        # if DEBUG_MODE:
        #     print("Initializing database for testing...")
        #     initialize_database()

        # Step 1: Scrape Results for match links
        self.logger.info("Scraping results page...")
        match_links = self.results_scraper.fetch_results()
        if not match_links:
            self.logger.warning("Match scraping failed.")
            return
        else:
            self.logger.info("Successfully scraped results page.")

        # Step 2 : Scrape each match page for raw match meta data
        self.logger.info("Parsing match details")
        match_meta_data: list[BeautifulSoup] = [
            self.match_scraper.fetch_match(match_link) for match_link in match_links[:1]
        ]
        if not match_meta_data:
            self.logger.warning("⚠️ No match meta data scraped.")
            return
        else:
            self.logger.info("Successfully scraped match meta data.")

        # Step 3 : Parse Match Meta Data
        self.logger.info("Parsing match meta data")
        match_details: list[Match] = [
            MatchParser.parse_match(match) for match in match_meta_data
        ]
        if not match_details:
            self.logger.warning("Error parsing match meta data.")
            return
        else:
            self.logger.info("Successfully parsed match meta data.")
        print(match_details)
        print(type(match_details))

        # Step 4 : Scrape Map Details from Match.map_links
        self.logger.info("Scraping map details")
        map_meta_data: list[BeautifulSoup] = [
            self.map_scraper.fetch_map(Match.match_links)
            for Match.match_links in match_links
        ]

        # Step 5 : Parse map meta data for player_stats as Player Objects
        self.logger.info("Parsing map meta data")
        player_stats: list[Player] = [MapParser.parse_map(map) for map in map_meta_data]

        # # Step 4 : Scrape Map Details from Match.map_links
        # self.logger.info("Scraping map details")
        # for map_link in Match.map_links:
        #     self.map_scaper.(map_link)
        # match_details = [
        #     self.match_scraper.fetch_match_data(url) for url in results[:1]
        # ]
        # if not match_details:
        #     self.logger.warning("⚠️ No match details scraped.")
        #     return

        # # ✅ Step 3: Store Data in the Database
        # self.logger.info("💾 Storing match data in the database...")
        # # ✅ Step 3: Store Data in the Database
        # self.logger.info("💾 Storing match data in the database...")
        # print("💾 Storing match data in the database...")
        # print(f"📊 Match Data:\n{match_details}")  # Print before inserting
        # self.db.store_matches(match_details)

        # self.logger.info("✅ Match data successfully stored.")
        # print("✅ Match data successfully stored.")  # Confirm if this prints

        # self.logger.info("✅ Match data successfully stored.")

        # self.logger.info("🚀 CS2 pipeline completed.")
