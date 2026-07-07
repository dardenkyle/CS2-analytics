"""Controller for scraping and recording match result links."""

import time

from cs2_analytics.controllers.retry_utils import (
    is_retryable_scraper_error,
    reset_scraper,
)
from cs2_analytics.exceptions import PipelineError
from cs2_analytics.ingestion_state import MatchIngestionState
from cs2_analytics.scrapers.results_scraper import ResultsScraper
from cs2_analytics.stage_services import ResultsStageService
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("results_controller")


class ResultsController:
    """Orchestrates the results scraping stage."""

    def __init__(self) -> None:
        self.scraper = ResultsScraper()
        self.match_state = MatchIngestionState()
        self.stage_service = ResultsStageService(match_state=self.match_state)

    def run(self, max_matches: int = 50) -> None:
        """Scrapes result pages and records match URLs for downstream stages."""
        logger.info("Running ResultsController with max_matches=%d", max_matches)

        max_attempts = 3
        scraper = self.scraper
        retries = 0
        terminal_failures = 0
        run_status = "failed"

        try:
            for attempt in range(1, max_attempts + 1):
                try:
                    recorded = 0
                    for batch in scraper.iter_match_batches(max_matches=max_matches):
                        recorded += self.stage_service.record_batch(batch)
                    run_status = "succeeded"
                    logger.info("ResultsController complete. recorded=%d", recorded)
                    return
                except Exception as e:
                    is_retryable = self._is_recoverable_scraper_error(e)
                    should_retry = attempt < max_attempts and is_retryable

                    if should_retry:
                        retries += 1
                        logger.warning(
                            "Retryable results scraper error (attempt %d/%d): %s",
                            attempt,
                            max_attempts,
                            e,
                        )
                        time.sleep(3.0 * attempt)
                        scraper = self._reset_scraper(scraper)
                        continue

                    terminal_failures += 1
                    if is_retryable:
                        logger.error(
                            "ResultsController exhausted retries after %d attempts; failing stage run.",
                            max_attempts,
                        )
                        failure_message = (
                            "Results stage failed after exhausting retries "
                            f"({attempt}/{max_attempts} attempts)."
                        )
                    else:
                        failure_message = (
                            "Results stage failed on non-retryable error "
                            f"at attempt {attempt}/{max_attempts}."
                        )
                    logger.exception(
                        "ResultsController failed on attempt %d/%d: %s",
                        attempt,
                        max_attempts,
                        e,
                    )
                    raise PipelineError(failure_message) from e
        finally:
            try:
                scraper.close()
            except Exception as e:
                logger.warning("Failed to close results scraper: %s", e)
            logger.info(
                "ResultsController summary: status=%s retries=%d terminal_failures=%d max_matches=%d",
                run_status,
                retries,
                terminal_failures,
                max_matches,
            )

    def _is_recoverable_scraper_error(self, error: Exception) -> bool:
        return is_retryable_scraper_error(error)

    def _reset_scraper(self, scraper: ResultsScraper) -> ResultsScraper:
        self.scraper = reset_scraper(
            scraper,
            ResultsScraper,
            logger=logger,
            close_warning_message="Failed to close results scraper during recovery: %s",
            startup_delay_seconds=1.0,
        )
        return self.scraper
