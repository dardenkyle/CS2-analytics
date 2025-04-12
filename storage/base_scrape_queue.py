from abc import ABC
from datetime import datetime
from typing import List, Tuple, Optional
from storage.database import get_connection


class BaseScrapeQueue(ABC):
    """
    Abstract base class for scrape queue management.

    This class encapsulates the common logic for managing queue tables
    such as inserting, fetching, marking as parsed or failed, and resetting.
    Subclasses should configure `table_name` and `id_field` appropriately.
    """

    def __init__(self, table_name: str, id_field: str) -> None:
        """
        Initialize the base queue with a specific table and ID field.

        Args:
            table_name (str): The name of the queue table in the database.
            id_field (str): The primary identifier field (e.g., 'demo_id').
        """
        self.table_name = table_name
        self.id_field = id_field

    def queue(
        self, id_value: str, url: str, source: str = "", priority: int = 0
    ) -> None:
        """
        Insert a new item into the queue.

        Args:
            id_value (str): Unique ID of the item.
            url (str): URL associated with the item (e.g., demo or match).
            source (str): Optional source label (e.g., 'manual', 'scraper').
            priority (int): Optional priority value for processing order.
        """
        query = f"""
            INSERT INTO {self.table_name} (
                {self.id_field}, {self.id_field.replace("_id", "_url")},
                status, inserted_at, last_updated_at,
                retry_count, last_error, priority, source
            )
            VALUES (%s, %s, 'queued', %s, %s, 0, NULL, %s, %s)
            ON CONFLICT ({self.id_field}) DO NOTHING;
        """
        now = datetime.utcnow()

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (id_value, url, now, now, priority, source))
                conn.commit()
        except Exception as e:
            print(f"❌ Failed to queue {id_value} in {self.table_name}: {e}")

    def fetch(self, limit: int = 50) -> List[Tuple[str, str]]:
        """
        Fetch items from the queue that are still pending and below retry threshold.

        Args:
            limit (int): Number of items to fetch (default: 50).

        Returns:
            List[Tuple[str, str]]: A list of (id, url) tuples.
        """
        url_field = self.id_field.replace("_id", "_url")
        query = f"""
            SELECT {self.id_field}, {url_field}
            FROM {self.table_name}
            WHERE status = 'queued' AND retry_count < 3
            ORDER BY priority DESC, last_updated_at ASC
            LIMIT %s;
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (limit,))
                    return cur.fetchall()
        except Exception as e:
            print(f"❌ Failed to fetch from {self.table_name}: {e}")
            return []

    def mark_parsed(self, id_value: str) -> None:
        """
        Mark an item as successfully parsed.

        Args:
            id_value (str): Unique identifier of the item.
        """
        query = f"""
            UPDATE {self.table_name}
            SET status = 'parsed', last_updated_at = %s
            WHERE {self.id_field} = %s;
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (datetime.utcnow(), id_value))
                conn.commit()
        except Exception as e:
            print(f"❌ Failed to mark {id_value} as parsed in {self.table_name}: {e}")

    def mark_failed(self, id_value: str, error_msg: Optional[str] = "") -> None:
        """
        Mark an item as failed and store error details.

        Args:
            id_value (str): Unique identifier of the item.
            error_msg (str): Optional error message to store.
        """
        query = f"""
            UPDATE {self.table_name}
            SET status = 'failed',
                last_updated_at = %s,
                retry_count = retry_count + 1,
                last_error = %s
            WHERE {self.id_field} = %s;
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (datetime.utcnow(), error_msg[:500], id_value))
                conn.commit()
        except Exception as e:
            print(f"❌ Failed to mark {id_value} as failed in {self.table_name}: {e}")

    def reset_failed(self, id_value: str) -> None:
        """
        Reset a failed item to 'queued' status and clear error info.

        Args:
            id_value (str): Unique identifier of the item.
        """
        query = f"""
            UPDATE {self.table_name}
            SET status = 'queued',
                retry_count = 0,
                last_error = NULL,
                last_updated_at = %s
            WHERE {self.id_field} = %s;
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (datetime.utcnow(), id_value))
                conn.commit()
        except Exception as e:
            print(f"❌ Failed to reset {id_value} in {self.table_name}: {e}")
