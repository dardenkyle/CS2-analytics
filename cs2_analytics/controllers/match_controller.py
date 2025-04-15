from cs2_analytics.scrapers.match_scraper import MatchScraper
from cs2_analytics.parsers.match_parser import MatchParser
from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
from cs2_analytics.queues.demo_scrape_queue import DemoScrapeQueue
from cs2_analytics.storage.match_storage import store_matches
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("match_controller")


class MatchController:
    def __init__(self) -> None:
        self.scraper = MatchScraper()
        self.parser = MatchParser()
        self.match_queue = MatchScrapeQueue()
        self.map_queue = MapScrapeQueue()
        self.demo_queue = DemoScrapeQueue()

    def run(self, batch_size: int = 25) -> None:
        logger.info("🕹️ Running MatchController with batch size: %d", batch_size)

        with self.scraper as scraper:
            queued = self.match_queue.fetch(limit=batch_size)
            logger.info("📥 %d matches pulled from queue", len(queued))

            for match_id, match_url in queued:
                try:
                    soup = scraper._fetch_soup(match_url)
                    match, map_links, demo_links = self.parser.parse_match(soup, match_url)

                    if match:
                        store_matches([match])
                        self._queue_followups(map_links, demo_links)
                        self.match_queue.mark_as_parsed(match_id)
                        logger.info("✅ Stored match: %s", match_id)
                    else:
                        self.match_queue.mark_as_failed(match_id, "Parsing returned None")
                        logger.warning("❌ Match %s returned None", match_id)

                except Exception as e:
                    self.match_queue.mark_as_failed(match_id, str(e)[:500])
                    logger.exception("❌ Error processing match %s: %s", match_id, e)

        logger.info("🏁 MatchController complete.")

    def _queue_followups(
        self,
        map_links: list[tuple[str, str]],
        demo_links: list[tuple[str, str]],
    ) -> None:
        """Queues map and demo links returned by the parser."""
        for map_id, map_url in map_links:
            self.map_queue.queue(map_id, map_url, source="match_parser")
        for demo_id, demo_url in demo_links:
            self.demo_queue.queue(demo_id, demo_url, source="match_parser")
