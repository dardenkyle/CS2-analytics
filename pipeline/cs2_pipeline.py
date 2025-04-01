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
from scrapers.map_scraper import MapScraper
from storage.database import Database
from utils.initialize_db import initialize_database
from utils.log_manager import get_logger


class CS2AnalyticsPipeline:
    """Controls the flow of the CS2 Analytics Pipeline."""

    def __init__(self) -> None:
        """Initialize pipeline components."""
        print("🚀 CS2AnalyticsPipeline Initialized!")  # ✅ Debug print
        self.logger = get_logger(__name__)
        self.logger.debug("CS2AnalyticsPipeline initialized.")

        self.results_scraper = ResultsScraper()
        self.match_scraper = MatchScraper()
        self.map_scraper = MapScraper()
        self.match_parser = MatchParser()
        self.map_parser = MapParser()
        self.db = Database()

    def run(self) -> None:
        """Execute the full CS2 analytics pipeline."""
        self.logger.info("✅ Starting full CS2 pipeline.")

        # if DEBUG_MODE:
        print("Initializing database for testing...")
        initialize_database()

        # Step 1: Scrape Results for match links
        self.logger.info("Scraping results page...")
        match_links = self.results_scraper.fetch_results()
        if not match_links:
            self.logger.warning("Match scraping failed.")
            return
        else:
            self.logger.info("Successfully scraped results page.")
            self.results_scraper.close()

        # Step 2 : Scrape each match page for raw match meta data
        self.logger.info("Parsing match details")
        match_meta_data: list[BeautifulSoup] = [
            self.match_scraper.fetch_match(match_link)
            for match_link in match_links[0:2]
        ]

        if not match_meta_data:
            self.logger.warning("No match meta data scraped.")
            return
        else:
            self.logger.info("Successfully scraped match meta data.")
            self.match_scraper.close()

        # Step 3 : Parse Match Meta Data
        self.logger.info("Parsing match meta data")
        match_details: list[Match] = [
            self.match_parser.parse_match(soup=soup, match_url=url)
            for soup, url in zip(match_meta_data, match_links)
        ]
        if not match_details:
            self.logger.warning("Error parsing match meta data.")
            return
        self.logger.info("Successfully parsed match meta data.")

        for match in match_details:
            print("Match links: %s", match.map_links)

        # Step 4 : Scrape Map Details from Match.map_links
        self.logger.info("Scraping map details")
        for match in match_details:
            map_meta_data: list[BeautifulSoup] = [
                self.map_scraper.fetch_map(url=link) for link in match.map_links
            ]

        map_urls_with_ids: list[tuple[str, int]] = [
            (map_url, match.match_id)
            for match in match_details
            for map_url in match.map_links
        ]

        # Step 5 : Parse map meta data for player_stats as Player Objects
        self.logger.info("Parsing map meta data")
        players_details: list[list[Player]] = []
        for soup, (map_url, match_id) in zip(map_meta_data, map_urls_with_ids):
            player_details: list[Player] = self.map_parser.parse_map(
                soup=soup, map_url=map_url, match_id=match_id
            )
            players_details.extend(player_details)

        # Convert to dictionaries
        match_details_dict: list[dict] = [match.to_dict() for match in match_details]
        player_details_dict: list[dict] = [
            player.to_dict() for player in players_details
        ]

        # Store data in the database
        try:
            self.db.store_matches(match_details_dict)
            self.logger.info("Stored %s matches successfully.", len(match_details_dict))
        except Exception as e:
            self.logger.error("Error storing match data: %s", e)
            return

        try:
            self.db.store_players(player_details_dict)
            self.logger.info(
                "Stored %s player stats successfully.", len(player_details_dict)
            )
        except Exception as e:
            self.logger.error("Error storing player data.: %s", e)
            return

        self.logger.info("🚀 CS2 pipeline completed.")
