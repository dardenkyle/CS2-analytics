import time
from contextlib import suppress

from cs2_analytics.parsers.map_parser import MapParser
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
from cs2_analytics.scrapers.map_scraper import MapScraper
from cs2_analytics.storage.player_storage import store_players
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("map_controller")


class MapController:
    def __init__(self) -> None:
        self.scraper = MapScraper()
        self.parser = MapParser()
        self.queue = MapScrapeQueue()

    def run(self, batch_size: int = 25) -> None:
        logger.info("🕹️ Running MapController with batch size: %d", batch_size)

        queued = self.queue.fetch(batch_size)
        logger.info("📥 %d map URLs pulled from queue", len(queued))

        rotate_every = 8
        inter_map_delay_seconds = 0.75
        retry_backoff_seconds = 3.0
        processed_since_reset = 0

        scraper = self.scraper
        try:
            for map_id, map_url in queued:
                if processed_since_reset >= rotate_every:
                    logger.info(
                        "🔁 Rotating map scraper session after %d processed maps",
                        processed_since_reset,
                    )
                    scraper = self._reset_scraper(scraper)
                    processed_since_reset = 0

                max_attempts = 3
                for attempt in range(1, max_attempts + 1):
                    try:
                        soup = scraper.fetch_soup(map_url)
                        player_obj = self.parser.parse_map(soup, map_url, map_id)

                        if player_obj:
                            store_players(player_obj)
                            self.queue.mark_as_parsed(map_id)
                            logger.info("✅ Stored map: %s", map_id)
                        else:
                            self.queue.mark_as_failed(map_id, "Parsing returned None")
                            logger.warning("❌ Map %s returned None", map_id)

                        processed_since_reset += 1
                        time.sleep(inter_map_delay_seconds)
                        break

                    except Exception as e:
                        should_retry = (
                            attempt < max_attempts
                            and self._is_recoverable_scraper_error(e)
                        )

                        if should_retry:
                            logger.warning(
                                "⚠️ Recoverable scraper error for map %s (attempt %d/%d): %s",
                                map_id,
                                attempt,
                                max_attempts,
                                e,
                            )
                            time.sleep(retry_backoff_seconds * attempt)
                            scraper = self._reset_scraper(scraper)
                            continue

                        self.queue.mark_as_failed(map_id, str(e)[:500])
                        logger.exception("❌ Error processing map %s: %s", map_id, e)
                        break
        finally:
            with suppress(Exception):
                scraper.close()

        logger.info("🏁 MapController complete.")

    def _is_recoverable_scraper_error(self, error: Exception) -> bool:
        msg = str(error).lower()
        recoverable_signatures = (
            "connection refused",
            "max retries exceeded",
            "failed to establish a new connection",
            "invalid session id",
            "session deleted",
            "disconnected",
            "read timed out",
        )
        return any(sig in msg for sig in recoverable_signatures)

    def _reset_scraper(self, scraper: MapScraper) -> MapScraper:
        try:
            scraper.close()
        except Exception as e:
            logger.warning("⚠️ Failed to close map scraper during recovery: %s", e)

        self.scraper = MapScraper()
        time.sleep(1.0)
        return self.scraper
