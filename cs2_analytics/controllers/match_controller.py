"""Controller for scraping and storing match-level data."""

import time
from contextlib import suppress

from cs2_analytics.controllers.retry_utils import (
    BatchRunState,
    is_retryable_scraper_error,
    mark_item_failed,
    reset_scraper,
)
from cs2_analytics.ingestion_state import (
    DemoIngestionState,
    MapIngestionState,
    MatchIngestionState,
)
from cs2_analytics.parsers.match_parser import MatchParser
from cs2_analytics.scrapers.match_scraper import MatchScraper
from cs2_analytics.stage_services import MatchStageService
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.storage.match_storage import store_matches
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("match_controller")

ROTATE_EVERY = 8
INTER_MATCH_DELAY_SECONDS = 1.1
RETRY_BACKOFF_SECONDS = 3.0
MAX_ATTEMPTS = 3
COOLDOWN_AFTER_CONSECUTIVE_ERRORS = 2
COOLDOWN_SECONDS = 8.0


class MatchController:
    """Coordinates match batches, retry policy, and scraper lifecycle."""

    def __init__(self) -> None:
        self.scraper = MatchScraper()
        self.parser = MatchParser()
        self.match_state = MatchIngestionState()
        self.map_state = MapIngestionState()
        self.demo_state = DemoIngestionState()
        self.stage_service = MatchStageService(
            parser=self.parser,
            store_matches=store_matches,
            match_state=self.match_state,
            map_state=self.map_state,
            demo_state=self.demo_state,
            db=get_db(),
        )

    def run(self, batch_size: int = 25) -> None:
        """Runs the match stage for a batch of pending match URLs."""
        logger.info("Running MatchController with batch size: %d", batch_size)

        selected = self.match_state.fetch(limit=batch_size)
        logger.info("%d pending matches selected from ingestion state", len(selected))

        run_state: BatchRunState[MatchScraper] = BatchRunState(scraper=self.scraper)
        try:
            for match_id, match_url in selected:
                self._rotate_scraper_if_due(run_state)
                self.match_state.mark_as_processing(match_id)
                self._process_match_with_retries(match_id, match_url, run_state)
        finally:
            with suppress(Exception):
                run_state.scraper.close()

        logger.info(
            "MatchController summary: selected=%d succeeded=%d failed=%d retries=%d",
            len(selected),
            run_state.succeeded,
            run_state.failed,
            run_state.retries,
        )
        logger.info("MatchController complete.")

    def _rotate_scraper_if_due(self, run_state: BatchRunState[MatchScraper]) -> None:
        """Swaps in a fresh scraper session after enough processed matches."""
        if run_state.processed_since_reset < ROTATE_EVERY:
            return
        logger.info(
            "Rotating scraper session after %d processed matches",
            run_state.processed_since_reset,
        )
        run_state.scraper = self._reset_scraper(run_state.scraper)
        run_state.processed_since_reset = 0

    def _process_match_with_retries(
        self, match_id: int, match_url: str, run_state: BatchRunState[MatchScraper]
    ) -> None:
        """Runs one match through the stage service, retrying transient errors."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                self._record_stage_outcome(match_id, match_url, run_state)
                return
            except Exception as e:
                if attempt < MAX_ATTEMPTS and self._is_recoverable_scraper_error(e):
                    self._recover_from_retryable_error(match_id, attempt, e, run_state)
                else:
                    self._mark_terminal_failure(match_id, attempt, e, run_state)
                    return

    def _record_stage_outcome(
        self, match_id: int, match_url: str, run_state: BatchRunState[MatchScraper]
    ) -> None:
        """Processes one match and applies success/pacing bookkeeping."""
        result = self.stage_service.process_item(
            match_id, match_url, scraper=run_state.scraper
        )
        if result.succeeded:
            run_state.succeeded += 1
            logger.info("Stored match: %s", match_id)
        else:
            run_state.failed += 1
            logger.warning(
                "Match %s was not processed: %s",
                match_id,
                result.message,
            )

        run_state.consecutive_recoverable_errors = 0
        run_state.processed_since_reset += 1
        time.sleep(INTER_MATCH_DELAY_SECONDS)

    def _recover_from_retryable_error(
        self,
        match_id: int,
        attempt: int,
        error: Exception,
        run_state: BatchRunState[MatchScraper],
    ) -> None:
        """Backs off, cools down if errors cluster, and resets the scraper."""
        run_state.retries += 1
        run_state.consecutive_recoverable_errors += 1
        logger.warning(
            "Retryable scraper error for match %s (attempt %d/%d): %s",
            match_id,
            attempt,
            MAX_ATTEMPTS,
            error,
        )

        if (
            run_state.consecutive_recoverable_errors
            >= COOLDOWN_AFTER_CONSECUTIVE_ERRORS
        ):
            logger.info(
                "Applying cooldown after %d consecutive recoverable errors",
                run_state.consecutive_recoverable_errors,
            )
            time.sleep(COOLDOWN_SECONDS)

        time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        run_state.scraper = self._reset_scraper(run_state.scraper)

    def _mark_terminal_failure(
        self,
        match_id: int,
        attempt: int,
        error: Exception,
        run_state: BatchRunState[MatchScraper],
    ) -> None:
        """Marks the match failed after a non-retryable or exhausted error."""
        if attempt == MAX_ATTEMPTS and self._is_recoverable_scraper_error(error):
            logger.error(
                "Exhausted retries for match %s after %d attempts; marking failed and continuing.",
                match_id,
                MAX_ATTEMPTS,
            )
        mark_item_failed(
            self.match_state,
            match_id,
            error,
            logger=logger,
            log_message=("Error processing match %s on attempt %d/%d: %s"),
            attempt=attempt,
            max_attempts=MAX_ATTEMPTS,
        )
        run_state.failed += 1
        run_state.consecutive_recoverable_errors = 0

    def _is_recoverable_scraper_error(self, error: Exception) -> bool:
        """Returns True for transient scraper failures worth retrying."""
        return bool(is_retryable_scraper_error(error))

    def _reset_scraper(self, scraper: MatchScraper) -> MatchScraper:
        """Closes and recreates the scraper so the next attempt gets a fresh session."""
        self.scraper = reset_scraper(
            scraper,
            MatchScraper,
            logger=logger,
            close_warning_message="Failed to close scraper during recovery: %s",
            startup_delay_seconds=1.5,
            health_check=self._is_scraper_session_ready,
            max_reset_attempts=3,
            between_attempt_delay_seconds=1.0,
            recovery_success_message="Scraper session recovered on reset attempt %d",
            not_ready_warning_message=(
                "New scraper session not ready on reset attempt %d/%d; retrying reset"
            ),
            fallback_warning_message=(
                "Returning scraper after reset retries; first request may still require retry"
            ),
            fallback_delay_seconds=1.5,
        )
        return self.scraper

    def _is_scraper_session_ready(self, scraper: MatchScraper) -> bool:
        """Performs a lightweight health check for a fresh Selenium session."""
        try:
            scraper.driver.get("about:blank")
            _ = scraper.driver.page_source
            return True
        except Exception as e:
            logger.warning("Scraper session health check failed: %s", e)
            return False
