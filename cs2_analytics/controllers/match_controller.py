"""Controller for scraping and storing match-level data."""

import time
from contextlib import suppress

from cs2_analytics.controllers.retry_utils import (
    is_retryable_scraper_error,
    mark_item_failed,
    reset_scraper,
)
from cs2_analytics.parsers.match_parser import MatchParser
from cs2_analytics.queues.demo_scrape_queue import DemoScrapeQueue
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue
from cs2_analytics.scrapers.match_scraper import MatchScraper
from cs2_analytics.storage.match_storage import store_matches
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("match_controller")


class MatchController:
    """Orchestrates match scraping, parsing, queueing, and storage."""

    def __init__(self) -> None:
        self.scraper = MatchScraper()
        self.parser = MatchParser()
        self.match_queue = MatchScrapeQueue()
        self.map_queue = MapScrapeQueue()
        self.demo_queue = DemoScrapeQueue()

    def run(self, batch_size: int = 25) -> None:
        """Runs the match stage for a batch of queued match URLs."""
        logger.info("Running MatchController with batch size: %d", batch_size)

        queued = self.match_queue.fetch(limit=batch_size)
        logger.info("%d matches pulled from queue", len(queued))

        rotate_every = 8
        inter_match_delay_seconds = 1.1
        retry_backoff_seconds = 3.0
        processed_since_reset = 0
        consecutive_recoverable_errors = 0
        succeeded = 0
        failed = 0
        retries = 0

        scraper = self.scraper
        try:
            for match_id, match_url in queued:
                if processed_since_reset >= rotate_every:
                    logger.info(
                        "Rotating scraper session after %d processed matches",
                        processed_since_reset,
                    )
                    scraper = self._reset_scraper(scraper)
                    processed_since_reset = 0

                max_attempts = 3
                for attempt in range(1, max_attempts + 1):
                    try:
                        soup = scraper.fetch_soup(match_url)
                        match, map_links, demo_links = self.parser.parse_match(
                            soup, match_url
                        )

                        if match:
                            store_matches([match])
                            self._queue_followups(map_links, demo_links)
                            self.match_queue.mark_as_parsed(match_id)
                            succeeded += 1
                            logger.info("Stored match: %s", match_id)
                        else:
                            self.match_queue.mark_as_failed(
                                match_id, "Parsing returned None"
                            )
                            failed += 1
                            logger.warning("Match %s returned no parsed data", match_id)

                        consecutive_recoverable_errors = 0
                        processed_since_reset += 1
                        time.sleep(inter_match_delay_seconds)
                        break

                    except Exception as e:
                        should_retry = (
                            attempt < max_attempts
                            and self._is_recoverable_scraper_error(e)
                        )

                        if should_retry:
                            retries += 1
                            consecutive_recoverable_errors += 1
                            logger.warning(
                                "Retryable scraper error for match %s (attempt %d/%d): %s",
                                match_id,
                                attempt,
                                max_attempts,
                                e,
                            )

                            if consecutive_recoverable_errors >= 2:
                                logger.info(
                                    "Applying cooldown after %d consecutive recoverable errors",
                                    consecutive_recoverable_errors,
                                )
                                time.sleep(8.0)

                            time.sleep(retry_backoff_seconds * attempt)
                            scraper = self._reset_scraper(scraper)
                            continue

                        if (
                            attempt == max_attempts
                            and self._is_recoverable_scraper_error(e)
                        ):
                            logger.error(
                                "Exhausted retries for match %s after %d attempts; marking failed and continuing.",
                                match_id,
                                max_attempts,
                            )
                        mark_item_failed(
                            self.match_queue,
                            match_id,
                            e,
                            logger=logger,
                            log_message=(
                                "Error processing match %s on attempt %d/%d: %s"
                            ),
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )
                        failed += 1
                        consecutive_recoverable_errors = 0
                        break
        finally:
            with suppress(Exception):
                scraper.close()

        logger.info(
            "MatchController summary: queued=%d succeeded=%d failed=%d retries=%d",
            len(queued),
            succeeded,
            failed,
            retries,
        )
        logger.info("MatchController complete.")

    def _is_recoverable_scraper_error(self, error: Exception) -> bool:
        """Returns True for transient scraper failures worth retrying."""
        return is_retryable_scraper_error(error)

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
