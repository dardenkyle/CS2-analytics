"""Demo ingestion state manager."""

from cs2_analytics.queues.demo_scrape_queue import DemoScrapeQueue


class DemoIngestionState(DemoScrapeQueue):
    """Primary ingestion-state alias for current demo queue behavior."""
