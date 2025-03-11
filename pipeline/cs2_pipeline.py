import datetime as dt
import time
from config import HLTV_URL, MAX_MATCHES, ENABLE_DEMO_DOWNLOADS, ENABLE_DATA_STORAGE
from scraping import MatchScraper
from parsing import DemoParser
from storage import DataManager
from log_manager import setup_logger

class CS2AnalyticsPipeline:
    """Main pipeline to run CS2 analytics scraper."""

    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.match_scraper = MatchScraper(MAX_MATCHES, HLTV_URL)
        self.demo_parser = DemoParser()
        self.data_manager = DataManager()

    def fetch_match_data(self) -> list:
        """Scrapes match data from HLTV."""
        try:
            self.logger.info("🔄 Scraping match data...")
            match_data = self.match_scraper.fetch_matches()
            self.logger.info(f"✅ Successfully fetched {len(match_data)} matches.")
            return match_data
        except Exception as e:
            self.logger.error(f"❌ Failed to scrape matches: {e}")
            return []

    def process_match_data(self, match_data: list) -> tuple[list, list]:
        """Processes match data and extracts player statistics."""
        match_list = []
        player_stats_list = []

        try:
            self.logger.info("🔄 Processing match data...")
            for match in match_data:
                try:
                    match_id = int(match["match_url"].split("/")[4])
                    match_list.append((
                        match_id, match["match_url"], match["team1"], match["team2"],
                        match["score1"], match["score2"], match["event"], match["date"]
                    ))

                    player_stats = self.match_scraper.fetch_player_stats(match["match_url"])
                    for player_name, stats in player_stats.items():
                        player_stats_list.append((
                            match_id, player_name, stats["kills"], stats["headshots"],
                            stats["assists"], stats["flash_assists"], stats["deaths"],
                            stats["kast"], stats["kd_diff"], stats["adr"], stats["fk_diff"], stats["rating"]
                        ))
                except (KeyError, IndexError, ValueError) as e:
                    self.logger.warning(f"⚠️ Skipping a match due to data parsing error: {e}")

            self.logger.info(f"✅ Processed {len(match_list)} matches and {len(player_stats_list)} player stats.")
            return match_list, player_stats_list
        except Exception as e:
            self.logger.error(f"❌ Error processing match data: {e}")
            return [], []

    def store_data(self, match_list: list, player_stats_list: list):
        """Stores match and player statistics in the database."""
        if ENABLE_DATA_STORAGE:
            try:
                self.logger.info("💾 Storing match and player data...")
                if match_list:
                    self.data_manager.store_match_data(match_list)
                if player_stats_list:
                    self.data_manager.store_player_data(player_stats_list)
                self.logger.info("✅ Data storage completed successfully.")
            except Exception as e:
                self.logger.error(f"❌ Error storing data: {e}")

    def download_and_parse_demos(self, match_list: list):
        """Downloads and parses demos if enabled."""
        if ENABLE_DEMO_DOWNLOADS:
            try:
                self.logger.info("📥 Downloading demo files...")
                self.demo_parser.download_demos(match_list)
                self.logger.info("📊 Parsing demo files...")
                self.demo_parser.parse_demos()
                self.logger.info("✅ Demo analysis completed.")
            except Exception as e:
                self.logger.error(f"❌ Error processing demos: {e}")

    def run(self, retry_attempts=3, retry_delay=5):
        """Executes the full pipeline with retry logic."""
        self.logger.info(f"🚀 Starting CS2 Analytics Pipeline at {dt.datetime.now()}")

        for attempt in range(retry_attempts):
            self.logger.info(f"🔄 Attempt {attempt + 1} of {retry_attempts}...")

            match_data = self.fetch_match_data()
            if not match_data:
                self.logger.warning("⚠️ No match data found. Retrying..." if attempt < retry_attempts - 1 else "❌ Giving up.")
                time.sleep(retry_delay)
                continue

            match_list, player_stats_list = self.process_match_data(match_data)

            self.store_data(match_list, player_stats_list)
            self.download_and_parse_demos(match_list)

            self.logger.info("✅ CS2 Analytics Pipeline completed!")
            return  # Exit if successful

        self.logger.error("❌ All retry attempts failed. Exiting pipeline.")
