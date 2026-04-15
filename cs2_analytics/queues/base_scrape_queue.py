"""Base class for managing scrape queues."""

import datetime as dt

from cs2_analytics.exceptions import QueueError
from cs2_analytics.storage.db_instance import db
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class BaseScrapeQueue:
    """
    Generic base class for scrape queues.
    Subclasses must define:
    - table_name: the DB table to use
    - id_field: the primary key field
    - url_field: the URL field name (e.g. match_url, map_url, demo_url)
    """

    def __init__(
        self,
        table_name: str,
        id_field: str,
        url_field: str,
        error_cls: type[QueueError] = QueueError,
    ):
        self.table_name = table_name
        self.id_field = id_field
        self.url_field = url_field
        self.error_cls = error_cls

    def fetch(self, limit: int = 25) -> list[tuple[str, str]]:
        """Fetches items with status='queued' from the queue."""
        query = f"""
        SELECT {self.id_field}, {self.url_field}
        FROM {self.table_name}
        WHERE status = 'queued'
        ORDER BY last_inserted_at ASC
        LIMIT %s;
        """
        try:
            with db.get_cursor() as cur:
                cur.execute(query, (limit,))
                return cur.fetchall()
        except Exception as e:
            raise self.error_cls(
                f"Failed to fetch queued items from {self.table_name}."
            ) from e

    def queue(
        self, id_value: str, url: str, source: str = "unknown", priority: int = 0
    ) -> None:
        """Adds a single item to the queue."""
        query = f"""
        INSERT INTO {self.table_name} ({self.id_field}, {self.url_field}, status, source, priority, last_inserted_at)
        VALUES (%s, %s, 'queued', %s, %s, %s)
        ON CONFLICT ({self.id_field}) DO NOTHING;
        """
        try:
            with db.get_cursor() as cur:
                cur.execute(
                    query, (id_value, url, source, priority, dt.datetime.now())
                )
        except Exception as e:
            raise self.error_cls(f"Failed to queue item in {self.table_name}.") from e

    def queue_many(
        self, items: list[tuple[str, str]], source: str = "unknown", priority: int = 0
    ) -> None:
        """Adds multiple items to the queue in batch."""
        if not items:
            return

        query = f"""
        INSERT INTO {self.table_name} ({self.id_field}, {self.url_field}, source, priority, last_inserted_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT ({self.id_field}) DO NOTHING;
        """

        values = [
            (item_id, url, source, priority, dt.datetime.now())
            for item_id, url in items
        ]

        try:
            with db.get_cursor() as cur:
                cur.executemany(query, values)
                logger.info("Queued %d items in %s", len(items), self.table_name)
        except Exception as e:
            raise self.error_cls(f"Failed to queue items in {self.table_name}.") from e

    def mark_as_parsed(self, id_value: str) -> None:
        """Marks the item as successfully processed."""
        query = f"""
        UPDATE {self.table_name}
        SET status = 'parsed', last_updated_at = %s
        WHERE {self.id_field} = %s;
        """
        try:
            with db.get_cursor() as cur:
                cur.execute(query, (dt.datetime.now(), id_value))
        except Exception as e:
            raise self.error_cls(
                f"Failed to mark item as parsed in {self.table_name}."
            ) from e

    def mark_as_failed(self, id_value: str, reason: str = "unknown") -> None:
        """Marks the item as failed and stores the reason."""
        query = f"""
        UPDATE {self.table_name}
        SET status = 'failed', last_updated_at = %s, last_error = %s
        WHERE {self.id_field} = %s;
        """
        try:
            with db.get_cursor() as cur:
                cur.execute(query, (dt.datetime.now(), reason, id_value))
        except Exception as e:
            raise self.error_cls(
                f"Failed to mark item as failed in {self.table_name}."
            ) from e

