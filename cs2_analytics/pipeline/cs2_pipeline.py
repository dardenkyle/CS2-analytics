from cs2_analytics.controllers.map_controller import MapController
from cs2_analytics.controllers.match_controller import MatchController
from cs2_analytics.controllers.results_controller import ResultsController
from cs2_analytics.utils.log_manager import get_logger


class CS2AnalyticsPipeline:
    """Orchestrates scraping, parsing, storing of CS2 data via controllers."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.results_controller = ResultsController()
        self.match_controller = MatchController()
        self.map_controller = MapController()

    def run(self) -> None:
        self.logger.info("🚀 CS2 Analytics Pipeline started.")

        # Step 1: Scrape results and record match links
        self.logger.info("🔍 Scraping match results page...")
        self.results_controller.run()

        # Step 2: Process pending matches from match_ingestion_state
        self.logger.info("🎯 Processing matches...")
        self.match_controller.run(batch_size=50)

        # Step 3: Process pending maps from map_ingestion_state
        self.logger.info("🗺️ Processing maps...")
        self.map_controller.run(batch_size=50)

        self.logger.info("✅ CS2 Analytics Pipeline complete.")
