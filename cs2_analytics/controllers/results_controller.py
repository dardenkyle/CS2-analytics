"""Controller for scraping and queuing match result links."""

import time

from cs2_analytics.exceptions import RetryableScrapeError
from cs2_analytics.scrapers.results_scraper import ResultsScraper
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("results_controller")


class ResultsController:
    """Orchestrates the results scraping stage."""

    def __init__(self) -> None:
        self.scraper = ResultsScraper()

    def run(self, max_matches: int = 50) -> None:
        """Scrapes result pages and queues match URLs for downstream stages."""
        logger.info("Running ResultsController with max_matches=%d", max_matches)

        max_attempts = 3
        scraper = self.scraper

        try:
            for attempt in range(1, max_attempts + 1):
                try:
                    scraper.run(max_matches=max_matches)
                    logger.info("ResultsController complete.")
                    return
                except Exception as e:
                    should_retry = (
                        attempt < max_attempts
                        and self._is_recoverable_scraper_error(e)
                    )

                    if should_retry:
                        logger.warning(
                            "Retryable results scraper error (attempt %d/%d): %s",
                            attempt,
                            max_attempts,
                            e,
                        )
                        time.sleep(3.0 * attempt)
                        scraper = self._reset_scraper(scraper)
                        continue

                    logger.exception(
                        "ResultsController failed on attempt %d/%d: %s",
                        attempt,
                        max_attempts,
                        e,
                    )
                    return
        finally:
            try:
                scraper.close()
            except Exception as e:
                logger.warning("Failed to close results scraper: %s", e)

    def _is_recoverable_scraper_error(self, error: Exception) -> bool:
        return isinstance(error, RetryableScrapeError)

    def _reset_scraper(self, scraper: ResultsScraper) -> ResultsScraper:
        try:
            scraper.close()
        except Exception as e:
            logger.warning("Failed to close results scraper during recovery: %s", e)

        self.scraper = ResultsScraper()
        time.sleep(1.0)
        return self.scraper
