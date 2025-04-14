"""Manages queue operations for map-level data scraping."""

from storage.base_scrape_queue import BaseScrapeQueue


class MapScrapeQueue(BaseScrapeQueue):
    """
    Queue manager for map metadata and statistics scraping tasks.

    Targets the 'map_scrape_queue' table with 'map_id' as the primary key.
    """

    def __init__(self) -> None:
        super().__init__(table_name="map_scrape_queue", id_field="map_id")
