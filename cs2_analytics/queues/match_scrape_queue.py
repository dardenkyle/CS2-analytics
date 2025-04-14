"""Manages queue operations for match result scraping."""

from cs2_analytics.queues.base_scrape_queue import BaseScrapeQueue


class MatchScrapeQueue(BaseScrapeQueue):
    """
    Queue manager for match result discovery and scraping tasks.

    Handles operations for inserting, fetching, and updating scrape status
    in the 'match_scrape_queue' table.
    """

    def __init__(self) -> None:
        super().__init__(table_name="match_scrape_queue", id_field="match_id", url_field="match_url")
