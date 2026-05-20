"""Base class for managing ingestion state tables."""

import datetime as dt

from cs2_analytics.exceptions import IngestionStateError
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class BaseIngestionState:
    """
    Generic base class for ingestion state tables.
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
        error_cls: type[IngestionStateError] = IngestionStateError,
    ):
        self.table_name = table_name
        self.id_field = id_field
        self.url_field = url_field
        self.error_cls = error_cls

    @property
    def db(self):
        """Return the shared database instance when an operation needs it."""
        return get_db()

    def fetch(self, limit: int = 25) -> list[tuple[int | str, str]]:
        """Fetches pending items from the ingestion state table."""
        query = f"""
        SELECT {self.id_field}, {self.url_field}
        FROM {self.table_name}
        WHERE status = 'pending'
        ORDER BY priority DESC, first_seen_at ASC
        LIMIT %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (limit,))
                return cur.fetchall()
        except Exception as e:
            raise self.error_cls(
                f"Failed to fetch pending items from {self.table_name}."
            ) from e

    def queue(
        self, id_value: int | str, url: str, source: str = "unknown", priority: int = 0
    ) -> None:
        """Adds or refreshes a single ingestion state row."""
        now = dt.datetime.now()
        query = f"""
        INSERT INTO {self.table_name} (
            {self.id_field}, {self.url_field}, status, source, priority,
            first_seen_at, last_seen_at, last_updated_at
        )
        VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s)
        ON CONFLICT ({self.id_field}) DO UPDATE
        SET {self.url_field} = EXCLUDED.{self.url_field},
            source = EXCLUDED.source,
            priority = GREATEST(
                COALESCE({self.table_name}.priority, 0),
                EXCLUDED.priority
            ),
            last_seen_at = EXCLUDED.last_seen_at,
            last_updated_at = EXCLUDED.last_updated_at;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (id_value, url, source, priority, now, now, now))
        except Exception as e:
            raise self.error_cls(
                f"Failed to record ingestion state item in {self.table_name}."
            ) from e

    def queue_many(
        self,
        items: list[tuple[int | str, str]],
        source: str = "unknown",
        priority: int = 0,
    ) -> None:
        """Adds or refreshes multiple ingestion state rows in batch."""
        if not items:
            return

        query = f"""
        INSERT INTO {self.table_name} (
            {self.id_field}, {self.url_field}, status, source, priority,
            first_seen_at, last_seen_at, last_updated_at
        )
        VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s)
        ON CONFLICT ({self.id_field}) DO UPDATE
        SET {self.url_field} = EXCLUDED.{self.url_field},
            source = EXCLUDED.source,
            priority = GREATEST(
                COALESCE({self.table_name}.priority, 0),
                EXCLUDED.priority
            ),
            last_seen_at = EXCLUDED.last_seen_at,
            last_updated_at = EXCLUDED.last_updated_at;
        """

        now = dt.datetime.now()
        values = [
            (item_id, url, source, priority, now, now, now) for item_id, url in items
        ]

        try:
            with self.db.get_cursor() as cur:
                cur.executemany(query, values)
                logger.info(
                    "Recorded or refreshed %d items in %s", len(items), self.table_name
                )
        except Exception as e:
            raise self.error_cls(
                f"Failed to record ingestion state items in {self.table_name}."
            ) from e

    def mark_as_processing(self, id_value: int | str) -> None:
        """Marks the item as actively being processed."""
        now = dt.datetime.now()
        query = f"""
        UPDATE {self.table_name}
        SET status = 'processing', last_attempted_at = %s, last_updated_at = %s
        WHERE {self.id_field} = %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (now, now, id_value))
        except Exception as e:
            raise self.error_cls(
                f"Failed to mark item as processing in {self.table_name}."
            ) from e

    def mark_as_parsed(self, id_value: int | str) -> None:
        """Compatibility method that marks the item as processed."""
        self.mark_as_processed(id_value)

    def mark_as_processed(self, id_value: int | str) -> None:
        """Marks the item as successfully processed."""
        now = dt.datetime.now()
        query = f"""
        UPDATE {self.table_name}
        SET status = 'processed', last_processed_at = %s, last_updated_at = %s
        WHERE {self.id_field} = %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (now, now, id_value))
        except Exception as e:
            raise self.error_cls(
                f"Failed to mark item as processed in {self.table_name}."
            ) from e

    def mark_as_failed(self, id_value: int | str, reason: str = "unknown") -> None:
        """Marks the item as failed and stores the reason."""
        now = dt.datetime.now()
        query = f"""
        UPDATE {self.table_name}
        SET status = 'failed',
            last_failed_at = %s,
            last_updated_at = %s,
            last_error_message = %s,
            failure_count = COALESCE(failure_count, 0) + 1
        WHERE {self.id_field} = %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (now, now, reason, id_value))
        except Exception as e:
            raise self.error_cls(
                f"Failed to mark item as failed in {self.table_name}."
            ) from e

    def mark_as_skipped(self, id_value: int | str, reason: str = "unknown") -> None:
        """Marks the item as intentionally skipped."""
        now = dt.datetime.now()
        query = f"""
        UPDATE {self.table_name}
        SET status = 'skipped',
            last_updated_at = %s,
            last_error_message = %s
        WHERE {self.id_field} = %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (now, reason, id_value))
        except Exception as e:
            raise self.error_cls(
                f"Failed to mark item as skipped in {self.table_name}."
            ) from e
