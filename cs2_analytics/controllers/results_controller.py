"""Controller for scraping and queuing match result links."""

from cs2_analytics.scrapers.results_scraper import ResultsScraper
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("results_controller")


class ResultsController:
    """Orchestrates the results scraping stage."""

    def __init__(self) -> None:
        self.scraper = ResultsScraper()

    def run(self, max_matches: int = 50) -> None:
        """Scrapes result pages and queues match URLs for downstream stages."""
        logger.info("🕹️ Running ResultsController with max_matches=%d", max_matches)
        with self.scraper as scraper:
            scraper.run(max_matches=max_matches)
        logger.info("🏁 ResultsController complete.")
