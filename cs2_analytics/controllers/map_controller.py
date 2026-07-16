"""Controller for scraping and storing map-level player data."""

import time
from contextlib import suppress

from cs2_analytics.controllers.retry_utils import (
    BatchRunState,
    is_retryable_scraper_error,
    mark_item_failed,
    reset_scraper,
)
from cs2_analytics.ingestion_state import MapIngestionState
from cs2_analytics.parsers.map_parser import MapParser
from cs2_analytics.scrapers.map_scraper import MapScraper
from cs2_analytics.stage_services import MapStageService
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.storage.map_storage import store_maps
from cs2_analytics.storage.player_storage import store_players
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("map_controller")

ROTATE_EVERY = 8
INTER_MAP_DELAY_SECONDS = 0.75
RETRY_BACKOFF_SECONDS = 3.0
MAX_ATTEMPTS = 3


class MapController:
    """Coordinates map batches, retry policy, and scraper lifecycle."""

    def __init__(self) -> None:
        self.scraper = MapScraper()
        self.parser = MapParser()
        self.state = MapIngestionState()
        self.stage_service = MapStageService(
            parser=self.parser,
            store_maps=store_maps,
            store_players=store_players,
            map_state=self.state,
            db=get_db(),
        )

    def run(self, batch_size: int = 25) -> None:
        logger.info("Running MapController with batch size: %d", batch_size)

        selected = self.state.fetch_with_match_context(batch_size)
        logger.info("%d pending maps selected from ingestion state", len(selected))

        run_state: BatchRunState[MapScraper] = BatchRunState(scraper=self.scraper)
        try:
            for map_id, map_url, match_id, map_order in selected:
                self._rotate_scraper_if_due(run_state)
                self.state.mark_as_processing(map_id)
                self._process_map_with_retries(
                    map_id, map_url, match_id, map_order, run_state
                )
        finally:
            with suppress(Exception):
                run_state.scraper.close()

        logger.info(
            "MapController summary: selected=%d succeeded=%d failed=%d retries=%d",
            len(selected),
            run_state.succeeded,
            run_state.failed,
            run_state.retries,
        )
        logger.info("MapController complete.")

    def _rotate_scraper_if_due(self, run_state: BatchRunState[MapScraper]) -> None:
        """Swaps in a fresh scraper session after enough processed maps."""
        if run_state.processed_since_reset < ROTATE_EVERY:
            return
        logger.info(
            "Rotating map scraper session after %d processed maps",
            run_state.processed_since_reset,
        )
        run_state.scraper = self._reset_scraper(run_state.scraper)
        run_state.processed_since_reset = 0

    def _process_map_with_retries(
        self,
        map_id: int,
        map_url: str,
        match_id: int | None,
        map_order: int | None,
        run_state: BatchRunState[MapScraper],
    ) -> None:
        """Runs one map through the stage service, retrying transient errors."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                self._record_stage_outcome(
                    map_id, map_url, match_id, map_order, run_state
                )
                return
            except Exception as e:
                if attempt < MAX_ATTEMPTS and self._is_recoverable_scraper_error(e):
                    self._recover_from_retryable_error(map_id, attempt, e, run_state)
                else:
                    self._mark_terminal_failure(map_id, attempt, e, run_state)
                    return

    def _record_stage_outcome(
        self,
        map_id: int,
        map_url: str,
        match_id: int | None,
        map_order: int | None,
        run_state: BatchRunState[MapScraper],
    ) -> None:
        """Processes one map and applies success/pacing bookkeeping."""
        result = self.stage_service.process_item(
            map_id,
            map_url,
            scraper=run_state.scraper,
            match_id=match_id,
            map_order=map_order,
        )
        if result.succeeded:
            run_state.succeeded += 1
            logger.info("Stored map: %s", map_id)
        else:
            run_state.failed += 1
            logger.warning(
                "Map %s was not processed: %s",
                map_id,
                result.message,
            )

        run_state.processed_since_reset += 1
        time.sleep(INTER_MAP_DELAY_SECONDS)

    def _recover_from_retryable_error(
        self,
        map_id: int,
        attempt: int,
        error: Exception,
        run_state: BatchRunState[MapScraper],
    ) -> None:
        """Backs off and resets the scraper before the next attempt."""
        run_state.retries += 1
        logger.warning(
            "Retryable scraper error for map %s (attempt %d/%d): %s",
            map_id,
            attempt,
            MAX_ATTEMPTS,
            error,
        )
        time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        run_state.scraper = self._reset_scraper(run_state.scraper)

    def _mark_terminal_failure(
        self,
        map_id: int,
        attempt: int,
        error: Exception,
        run_state: BatchRunState[MapScraper],
    ) -> None:
        """Marks the map failed after a non-retryable or exhausted error."""
        if attempt == MAX_ATTEMPTS and self._is_recoverable_scraper_error(error):
            logger.error(
                "Exhausted retries for map %s after %d attempts; marking failed and continuing.",
                map_id,
                MAX_ATTEMPTS,
            )
        mark_item_failed(
            self.state,
            map_id,
            error,
            logger=logger,
            log_message="Error processing map %s on attempt %d/%d: %s",
            attempt=attempt,
            max_attempts=MAX_ATTEMPTS,
        )
        run_state.failed += 1

    def _is_recoverable_scraper_error(self, error: Exception) -> bool:
        return is_retryable_scraper_error(error)

    def _reset_scraper(self, scraper: MapScraper) -> MapScraper:
        self.scraper = reset_scraper(
            scraper,
            MapScraper,
            logger=logger,
            close_warning_message="Failed to close map scraper during recovery: %s",
            startup_delay_seconds=1.0,
        )
        return self.scraper
