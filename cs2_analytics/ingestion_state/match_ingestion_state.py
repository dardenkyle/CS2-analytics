"""Match ingestion state manager."""

from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue


class MatchIngestionState(MatchScrapeQueue):
    """Primary ingestion-state alias for current match queue behavior."""
