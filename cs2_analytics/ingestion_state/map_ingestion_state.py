"""Map ingestion state manager."""

from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue


class MapIngestionState(MapScrapeQueue):
    """Primary ingestion-state alias for current map queue behavior."""
