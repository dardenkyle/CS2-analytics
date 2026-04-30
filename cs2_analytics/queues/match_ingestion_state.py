"""Compatibility name for match ingestion state management."""

from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue


class MatchIngestionState(MatchScrapeQueue):
    """Alias class for the current match scrape queue implementation."""
