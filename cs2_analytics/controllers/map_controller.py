from cs2_analytics.scrapers.map_scraper import MapScraper
from cs2_analytics.parsers.map_parser import MapParser
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
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

        with self.scraper as scraper:
            queued = self.queue.fetch(batch_size)
            logger.info("📥 %d map URLs pulled from queue", len(queued))

            for map_id, map_url in queued:
                try:
                    soup = scraper._fetch_soup(map_url)
                    player_obj = self.parser.parse_map(soup, map_url, map_id)

                    if player_obj:
                        store_players(player_obj)
                        self.queue.mark_as_parsed(map_id)
                        logger.info("✅ Stored map: %s", map_id)
                    else:
                        self.queue.mark_as_failed(map_id, "Parsing returned None")
                        logger.warning("❌ Map %s returned None", map_id)

                except Exception as e:
                    self.queue.mark_as_failed(map_id, str(e))
                    logger.exception("❌ Error processing map %s: %s", map_id, e)

        logger.info("🏁 MapController complete.")
