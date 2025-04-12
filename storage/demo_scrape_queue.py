"""Manages queue operations for demo file scraping."""

from storage.base_scrape_queue import BaseScrapeQueue


class DemoScrapeQueue(BaseScrapeQueue):
    """
    Queue manager for .dem file downloads and parsing tasks.

    Table: demo_scrape_queue
    ID field: demo_id
    """

    def __init__(self) -> None:
        super().__init__(table_name="demo_scrape_queue", id_field="demo_id")
