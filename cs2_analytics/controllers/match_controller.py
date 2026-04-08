"""This module contains the MatchController class, which orchestrates the scraping and parsing of match data."""

import time
from contextlib import suppress

from cs2_analytics.parsers.match_parser import MatchParser
from cs2_analytics.queues.demo_scrape_queue import DemoScrapeQueue
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue
from cs2_analytics.scrapers.match_scraper import MatchScraper
from cs2_analytics.storage.match_storage import store_matches
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("match_controller")


class MatchController:
    """
    MatchController orchestrates the scraping and parsing of match data."""

    def __init__(self) -> None:
        self.scraper = MatchScraper()
        self.parser = MatchParser()
        self.match_queue = MatchScrapeQueue()
        self.map_queue = MapScrapeQueue()
        self.demo_queue = DemoScrapeQueue()

    def run(self, batch_size: int = 25) -> None:
        """
        Main method to run the MatchController.

        Args:
            batch_size (int): Number of matches to process in each batch.
        """
        logger.info("🕹️ Running MatchController with batch size: %d", batch_size)

        queued = self.match_queue.fetch(limit=batch_size)
        logger.info("📥 %d matches pulled from queue", len(queued))

        # Refresh browser session before it reaches the observed instability window.
        rotate_every = 8
        inter_match_delay_seconds = 1.1
        retry_backoff_seconds = 3.0
        processed_since_reset = 0
        consecutive_recoverable_errors = 0

        scraper = self.scraper
        try:
            for match_id, match_url in queued:
                if processed_since_reset >= rotate_every:
                    logger.info(
                        "🔁 Rotating scraper session after %d processed matches",
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
                            logger.info("✅ Stored match: %s", match_id)
                        else:
                            self.match_queue.mark_as_failed(
                                match_id, "Parsing returned None"
                            )
                            logger.warning("❌ Match %s returned None", match_id)

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
                            consecutive_recoverable_errors += 1
                            logger.warning(
                                "⚠️ Recoverable scraper error for match %s (attempt %d/%d): %s",
                                match_id,
                                attempt,
                                max_attempts,
                                e,
                            )

                            if consecutive_recoverable_errors >= 2:
                                logger.info(
                                    "🧊 Applying cooldown after %d consecutive recoverable errors",
                                    consecutive_recoverable_errors,
                                )
                                time.sleep(8.0)

                            time.sleep(retry_backoff_seconds * attempt)
                            scraper = self._reset_scraper(scraper)
                            continue

                        self.match_queue.mark_as_failed(match_id, str(e)[:500])
                        logger.exception(
                            "❌ Error processing match %s: %s", match_id, e
                        )
                        consecutive_recoverable_errors = 0
                        break
        finally:
            with suppress(Exception):
                scraper.close()

        logger.info("🏁 MatchController complete.")

    def _is_recoverable_scraper_error(self, error: Exception) -> bool:
        """Returns True for transient Selenium/session failures worth retrying once."""
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

    def _reset_scraper(self, scraper: MatchScraper) -> MatchScraper:
        """Closes and recreates the scraper so the next attempt gets a fresh session."""
        try:
            scraper.close()
        except Exception as e:
            logger.warning("⚠️ Failed to close scraper during recovery: %s", e)

        for reset_attempt in range(1, 4):
            self.scraper = MatchScraper()
            # Give the new browser session a brief moment to fully initialize.
            time.sleep(1.5)

            if self._is_scraper_session_ready(self.scraper):
                if reset_attempt > 1:
                    logger.info(
                        "✅ Scraper session recovered on reset attempt %d",
                        reset_attempt,
                    )
                return self.scraper

            logger.warning(
                "⚠️ New scraper session not ready on reset attempt %d/3; retrying reset",
                reset_attempt,
            )
            with suppress(Exception):
                self.scraper.close()
            time.sleep(1.0)

        logger.warning(
            "⚠️ Returning scraper after reset retries; first request may still require retry"
        )
        self.scraper = MatchScraper()
        time.sleep(1.5)
        return self.scraper

    def _is_scraper_session_ready(self, scraper: MatchScraper) -> bool:
        """Performs a lightweight health check for a fresh Selenium session."""
        try:
            scraper.driver.get("about:blank")
            _ = scraper.driver.page_source
            return True
        except Exception as e:
            logger.warning("⚠️ Scraper session health check failed: %s", e)
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
