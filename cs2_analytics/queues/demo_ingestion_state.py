"""Compatibility name for demo ingestion state management."""

from cs2_analytics.queues.demo_scrape_queue import DemoScrapeQueue


class DemoIngestionState(DemoScrapeQueue):
    """Alias class for the current demo scrape queue implementation."""
