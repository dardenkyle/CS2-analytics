"""Controller for scraping and storing map-level player data."""

import time
from contextlib import suppress

from cs2_analytics.controllers.retry_utils import (
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

        rotate_every = 8
        inter_map_delay_seconds = 0.75
        retry_backoff_seconds = 3.0
        processed_since_reset = 0
        succeeded = 0
        failed = 0
        retries = 0

        scraper = self.scraper
        try:
            for map_id, map_url, match_id, map_order in selected:
                if processed_since_reset >= rotate_every:
                    logger.info(
                        "Rotating map scraper session after %d processed maps",
                        processed_since_reset,
                    )
                    scraper = self._reset_scraper(scraper)
                    processed_since_reset = 0

                self.state.mark_as_processing(map_id)
                max_attempts = 3
                for attempt in range(1, max_attempts + 1):
                    try:
                        result = self.stage_service.process_item(
                            map_id,
                            map_url,
                            scraper=scraper,
                            match_id=match_id,
                            map_order=map_order,
                        )
                        if result.succeeded:
                            succeeded += 1
                            logger.info("Stored map: %s", map_id)
                        else:
                            failed += 1
                            logger.warning(
                                "Map %s was not processed: %s",
                                map_id,
                                result.message,
                            )

                        processed_since_reset += 1
                        time.sleep(inter_map_delay_seconds)
                        break

                    except Exception as e:
                        should_retry = (
                            attempt < max_attempts
                            and self._is_recoverable_scraper_error(e)
                        )

                        if should_retry:
                            retries += 1
                            logger.warning(
                                "Retryable scraper error for map %s (attempt %d/%d): %s",
                                map_id,
                                attempt,
                                max_attempts,
                                e,
                            )
                            time.sleep(retry_backoff_seconds * attempt)
                            scraper = self._reset_scraper(scraper)
                            continue

                        if (
                            attempt == max_attempts
                            and self._is_recoverable_scraper_error(e)
                        ):
                            logger.error(
                                "Exhausted retries for map %s after %d attempts; marking failed and continuing.",
                                map_id,
                                max_attempts,
                            )
                        mark_item_failed(
                            self.state,
                            map_id,
                            e,
                            logger=logger,
                            log_message="Error processing map %s on attempt %d/%d: %s",
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )
                        failed += 1
                        break
        finally:
            with suppress(Exception):
                scraper.close()

        logger.info(
            "MapController summary: selected=%d succeeded=%d failed=%d retries=%d",
            len(selected),
            succeeded,
            failed,
            retries,
        )
        logger.info("MapController complete.")

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
