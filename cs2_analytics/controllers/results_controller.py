"""Controller for scraping and recording match result links."""

import time
from dataclasses import dataclass

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

RETRY_BACKOFF_SECONDS = 3.0
MAX_ATTEMPTS = 3


@dataclass
class _ResultsRunState:
    """Tracks the active scraper and outcome counters for one results run."""

    scraper: ResultsScraper
    status: str = "failed"
    retries: int = 0
    terminal_failures: int = 0


class ResultsController:
    """Orchestrates the results scraping stage."""

    def __init__(self) -> None:
        self.scraper = ResultsScraper()
        self.match_state = MatchIngestionState()
        self.stage_service = ResultsStageService(match_state=self.match_state)

    def run(self, max_matches: int = 50) -> None:
        """Scrapes result pages and records match URLs for downstream stages."""
        logger.info("Running ResultsController with max_matches=%d", max_matches)

        run_state = _ResultsRunState(scraper=self.scraper)
        try:
            self._run_attempts(max_matches, run_state)
        finally:
            self._close_scraper(run_state)
            logger.info(
                "ResultsController summary: status=%s retries=%d terminal_failures=%d max_matches=%d",
                run_state.status,
                run_state.retries,
                run_state.terminal_failures,
                max_matches,
            )

    def _run_attempts(self, max_matches: int, run_state: _ResultsRunState) -> None:
        """Attempts the results stage until it succeeds or retries are exhausted."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                recorded = self._record_discovered_batches(max_matches, run_state)
                run_state.status = "succeeded"
                logger.info("ResultsController complete. recorded=%d", recorded)
                return
            except Exception as e:
                self._handle_attempt_failure(e, attempt, run_state)

    def _record_discovered_batches(
        self, max_matches: int, run_state: _ResultsRunState
    ) -> int:
        """Streams result pages and records each discovered match batch."""
        recorded = 0
        for batch in run_state.scraper.iter_match_batches(max_matches=max_matches):
            recorded += self.stage_service.record_batch(batch)
        return recorded

    def _handle_attempt_failure(
        self, error: Exception, attempt: int, run_state: _ResultsRunState
    ) -> None:
        """Backs off and resets for retryable errors; raises PipelineError otherwise."""
        is_retryable = self._is_recoverable_scraper_error(error)

        if attempt < MAX_ATTEMPTS and is_retryable:
            run_state.retries += 1
            logger.warning(
                "Retryable results scraper error (attempt %d/%d): %s",
                attempt,
                MAX_ATTEMPTS,
                error,
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            run_state.scraper = self._reset_scraper(run_state.scraper)
            return

        run_state.terminal_failures += 1
        if is_retryable:
            logger.error(
                "ResultsController exhausted retries after %d attempts; failing stage run.",
                MAX_ATTEMPTS,
            )
            failure_message = (
                "Results stage failed after exhausting retries "
                f"({attempt}/{MAX_ATTEMPTS} attempts)."
            )
        else:
            failure_message = (
                "Results stage failed on non-retryable error "
                f"at attempt {attempt}/{MAX_ATTEMPTS}."
            )
        logger.exception(
            "ResultsController failed on attempt %d/%d: %s",
            attempt,
            MAX_ATTEMPTS,
            error,
        )
        raise PipelineError(failure_message) from error

    def _close_scraper(self, run_state: _ResultsRunState) -> None:
        """Closes the active scraper, downgrading close failures to a warning."""
        try:
            run_state.scraper.close()
        except Exception as e:
            logger.warning("Failed to close results scraper: %s", e)

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
