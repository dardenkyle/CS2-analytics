from cs2_analytics.ingestion_state import DemoIngestionState
from cs2_analytics.parsers.demo_parser import DemoParser
from cs2_analytics.scrapers.demo_scraper import DemoScraper
from cs2_analytics.stage_services import DemoStageService
from cs2_analytics.storage.demo_storage import store_demo_file
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("demo_controller")


class DemoController:
    def __init__(self) -> None:
        self.scraper = DemoScraper()
        self.parser = DemoParser()
        self.queue = DemoIngestionState()
        self.stage_service = DemoStageService(
            scraper=self.scraper,
            parser=self.parser,
            store_demo_file=store_demo_file,
            demo_state=self.queue,
        )

    def run(self, batch_size: int = 25) -> None:
        logger.info("🕹️ Running DemoController with batch size: %d", batch_size)

        queued = self.queue.fetch(batch_size)
        logger.info("📥 %d demo URLs pulled from queue", len(queued))
        succeeded = 0
        failed = 0

        for demo_id, demo_url in queued:
            try:
                self.queue.mark_as_processing(demo_id)
                stored = self.stage_service.process_item(demo_id, demo_url)

                if stored:
                    succeeded += 1
                    logger.info("✅ Stored demo: %s", demo_id)
                else:
                    failed += 1
                    logger.info(
                        "Demo %s was not stored by the demo stage service",
                        demo_id,
                    )

            except Exception as e:
                failed += 1
                self.queue.mark_as_failed(demo_id, str(e))
                logger.exception("❌ Error processing demo %s: %s", demo_id, e)

        logger.info(
            "DemoController summary: queued=%d succeeded=%d failed=%d",
            len(queued),
            succeeded,
            failed,
        )
        logger.info("🏁 DemoController complete.")
