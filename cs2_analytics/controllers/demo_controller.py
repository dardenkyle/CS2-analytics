from cs2_analytics.ingestion_state import DemoIngestionState
from cs2_analytics.parsers.demo_parser import DemoParser
from cs2_analytics.scrapers.demo_scraper import DemoScraper
from cs2_analytics.storage.demo_storage import store_demo_file
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("demo_controller")


class DemoController:
    def __init__(self) -> None:
        self.scraper = DemoScraper()
        self.parser = DemoParser()
        self.queue = DemoIngestionState()

    def run(self, batch_size: int = 25) -> None:
        logger.info("🕹️ Running DemoController with batch size: %d", batch_size)

        queued = self.queue.fetch(batch_size)
        logger.info("📥 %d demo URLs pulled from queue", len(queued))

        for demo_id, demo_url in queued:
            try:
                self.queue.mark_as_processing(demo_id)
                demo_path = self.scraper.download(demo_url)
                demo_obj = self.parser.parse_demo(demo_path, demo_url)

                if demo_obj:
                    store_demo_file([demo_obj])
                    self.queue.mark_as_parsed(demo_id)
                    logger.info("✅ Stored demo: %s", demo_id)
                else:
                    self.queue.mark_as_failed(demo_id, "Parsing returned None")
                    logger.warning("❌ Demo %s returned None", demo_id)

            except Exception as e:
                self.queue.mark_as_failed(demo_id, str(e))
                logger.exception("❌ Error processing demo %s: %s", demo_id, e)

        logger.info("🏁 DemoController complete.")
