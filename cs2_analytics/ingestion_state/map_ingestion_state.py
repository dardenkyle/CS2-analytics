"""Compatibility name for map ingestion state management."""

from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue


class MapIngestionState(MapScrapeQueue):
    """Alias class for the current map scrape queue implementation."""
