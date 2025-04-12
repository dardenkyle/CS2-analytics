"""Manages queue operations for map-level data scraping."""

from storage.base_scrape_queue import BaseScrapeQueue


class MapScrapeQueue(BaseScrapeQueue):
    """
    Queue manager for per-map statistics and metadata scraping tasks.

    Table: map_scrape_queue
    ID field: map_id
    """

    def __init__(self) -> None:
        super().__init__(table_name="map_scrape_queue", id_field="map_id")
