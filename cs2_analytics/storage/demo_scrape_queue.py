"""Manages queue operations for demo file scraping and processing."""

from storage.base_scrape_queue import BaseScrapeQueue


class DemoScrapeQueue(BaseScrapeQueue):
    """
    Queue manager for .dem file downloads and parsing tasks.

    Interacts with the 'demo_scrape_queue' table using 'demo_id' as the key.
    """

    def __init__(self) -> None:
        super().__init__(table_name="demo_scrape_queue", id_field="demo_id")
