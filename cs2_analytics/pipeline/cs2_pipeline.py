from cs2_analytics.controllers.match_controller import MatchController
from cs2_analytics.controllers.map_controller import MapController
from cs2_analytics.controllers.demo_controller import DemoController
from cs2_analytics.scrapers.results_scraper import ResultsScraper
from cs2_analytics.utils.log_manager import get_logger


class CS2AnalyticsPipeline:
    """Orchestrates scraping, parsing, storing of CS2 data via controllers."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.results_scraper = ResultsScraper()
        self.match_controller = MatchController()
        self.map_controller = MapController()
        self.demo_controller = DemoController()

    def run(self) -> None:
        self.logger.info("🚀 CS2 Analytics Pipeline started.")

        # Step 1: Scrape results and queue match links
        self.logger.info("🔍 Scraping match results page...")
        with self.results_scraper as scraper:
            scraper.run(max_matches=50)

        # Step 2: Process matches from match_scrape_queue
        self.logger.info("🎯 Processing matches...")
        self.match_controller.run(batch_size=10)

        # Step 3: Process maps from map_scrape_queue
        self.logger.info("🗺️ Processing maps...")
        self.map_controller.run(batch_size=10)

        # # Step 4: Process demos from demo_scrape_queue
        # self.logger.info("📦 Processing demos...")
        # self.demo_controller.run(batch_size=10)

        self.logger.info("✅ CS2 Analytics Pipeline complete.")
