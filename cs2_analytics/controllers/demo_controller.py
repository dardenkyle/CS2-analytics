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
        self.state = DemoIngestionState()
        self.stage_service = DemoStageService(
            scraper=self.scraper,
            parser=self.parser,
            store_demo_file=store_demo_file,
            demo_state=self.state,
        )

    def run(self, batch_size: int = 25) -> None:
        logger.info("Running DemoController with batch size: %d", batch_size)

        selected = self.state.fetch(batch_size)
        logger.info("%d pending demos selected from ingestion state", len(selected))
        succeeded = 0
        failed = 0
        skipped = 0

        for demo_id, demo_url in selected:
            try:
                self.state.mark_as_processing(demo_id)
                result = self.stage_service.process_item(demo_id, demo_url)

                if result.succeeded:
                    succeeded += 1
                    logger.info("Stored demo: %s", demo_id)
                elif result.status == "skipped":
                    skipped += 1
                    logger.info("Demo %s skipped: %s", demo_id, result.message)
                else:
                    failed += 1
                    logger.info(
                        "Demo %s was not processed: %s",
                        demo_id,
                        result.message,
                    )

            except Exception as e:
                failed += 1
                self.state.mark_as_failed(demo_id, str(e))
                logger.exception("Error processing demo %s: %s", demo_id, e)

        logger.info(
            "DemoController summary: selected=%d succeeded=%d failed=%d skipped=%d",
            len(selected),
            succeeded,
            failed,
            skipped,
        )
        logger.info("DemoController complete.")
