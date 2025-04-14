"""Abstract base class for managing scrape queue operations."""

from abc import ABC
from datetime import datetime
from typing import List, Tuple, Optional

from storage.db_instance import db
from utils.log_manager import get_logger

logger = get_logger(__name__)


class BaseScrapeQueue(ABC):
    """
    Abstract base class for scrape queue management.

    Encapsulates shared logic for inserting, fetching, marking parsed/failed,
    and resetting scrape tasks across queue tables.
    """

    def __init__(self, table_name: str, id_field: str) -> None:
        """
        Args:
            table_name (str): Name of the queue table in the database.
            id_field (str): Primary key field name (e.g., 'match_id').
        """
        self.table_name = table_name
        self.id_field = id_field

    def queue(
        self,
        id_value: str,
        url: str,
        source: str = "",
        priority: int = 0,
    ) -> None:
        """
        Inserts a single item into the queue.

        Args:
            id_value: Unique identifier.
            url: URL associated with the item.
            source: Optional origin label (e.g., 'results_scraper').
            priority: Optional priority value (higher = sooner).
        """
        now = datetime.utcnow()
        query = f"""
            INSERT INTO {self.table_name} (
                {self.id_field}, {self.id_field.replace("_id", "_url")},
                status, inserted_at, last_updated_at,
                retry_count, last_error, priority, source
            )
            VALUES (%s, %s, 'queued', %s, %s, 0, NULL, %s, %s)
            ON CONFLICT ({self.id_field}) DO NOTHING;
        """

        conn = db.get_connection()
        if conn is None:
            logger.error("❌ Could not get DB connection for queue insert.")
            return

        try:
            with conn.cursor() as cur:
                cur.execute(query, (id_value, url, now, now, priority, source))
            conn.commit()
        except Exception as e:
            logger.error(
                "❌ Failed to queue %s in %s: %s", id_value, self.table_name, e
            )
        finally:
            db.release_connection(conn)

    def queue_many(
        self,
        items: List[Tuple[str, str]],
        source: str = "",
        priority: int = 0,
    ) -> None:
        """
        Batch insert multiple items into the queue.

        Args:
            items: List of (id, url) tuples.
            source: Optional source label.
            priority: Optional priority score.
        """
        now = datetime.utcnow()
        values = [(item_id, url, now, now, priority, source) for item_id, url in items]

        query = f"""
            INSERT INTO {self.table_name} (
                {self.id_field}, {self.id_field.replace("_id", "_url")},
                status, inserted_at, last_updated_at,
                retry_count, last_error, priority, source
            )
            VALUES (%s, %s, 'queued', %s, %s, 0, NULL, %s, %s)
            ON CONFLICT ({self.id_field}) DO NOTHING;
        """

        conn = db.get_connection()
        if conn is None:
            logger.error("❌ Could not get DB connection for batch insert.")
            return

        try:
            with conn.cursor() as cur:
                cur.executemany(query, values)
            conn.commit()
            logger.info(
                "✅ Batch inserted %d rows into %s", len(items), self.table_name
            )
        except Exception as e:
            logger.error("❌ Failed batch insert into %s: %s", self.table_name, e)
        finally:
            db.release_connection(conn)

    def fetch(self, limit: int = 50) -> List[Tuple[str, str]]:
        """
        Fetches queued items that have not failed more than 3 times.

        Args:
            limit: Max number of records to retrieve.

        Returns:
            List of (id, url) tuples.
        """
        url_field = self.id_field.replace("_id", "_url")
        query = f"""
            SELECT {self.id_field}, {url_field}
            FROM {self.table_name}
            WHERE status = 'queued' AND retry_count < 3
            ORDER BY priority DESC, last_updated_at ASC
            LIMIT %s;
        """

        conn = db.get_connection()
        if conn is None:
            logger.error("❌ Could not get DB connection for fetch.")
            return []

        try:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                return cur.fetchall()
        except Exception as e:
            logger.error("❌ Failed to fetch from %s: %s", self.table_name, e)
            return []
        finally:
            db.release_connection(conn)

    def mark_parsed(self, id_value: str) -> None:
        """
        Marks an item as successfully parsed.

        Args:
            id_value: Unique ID to update.
        """
        query = f"""
            UPDATE {self.table_name}
            SET status = 'parsed', last_updated_at = %s
            WHERE {self.id_field} = %s;
        """

        conn = db.get_connection()
        if conn is None:
            logger.error("❌ Could not get DB connection to mark parsed.")
            return

        try:
            with conn.cursor() as cur:
                cur.execute(query, (datetime.utcnow(), id_value))
            conn.commit()
            logger.debug("✅ Marked %s as parsed in %s", id_value, self.table_name)
        except Exception as e:
            logger.error(
                "❌ Failed to mark %s as parsed in %s: %s", id_value, self.table_name, e
            )
        finally:
            db.release_connection(conn)

    def mark_failed(self, id_value: str, error_msg: Optional[str] = "") -> None:
        """
        Marks an item as failed and increments retry count.

        Args:
            id_value: Unique ID to update.
            error_msg: Optional error string (truncated to 500 chars).
        """
        query = f"""
            UPDATE {self.table_name}
            SET status = 'failed',
                last_updated_at = %s,
                retry_count = retry_count + 1,
                last_error = %s
            WHERE {self.id_field} = %s;
        """

        conn = db.get_connection()
        if conn is None:
            logger.error("❌ Could not get DB connection to mark failed.")
            return

        try:
            with conn.cursor() as cur:
                cur.execute(query, (datetime.utcnow(), error_msg[:500], id_value))
            conn.commit()
            logger.warning("⚠️ Marked %s as failed in %s", id_value, self.table_name)
        except Exception as e:
            logger.error(
                "❌ Failed to mark %s as failed in %s: %s", id_value, self.table_name, e
            )
        finally:
            db.release_connection(conn)

    def reset_failed(self, id_value: str) -> None:
        """
        Resets a failed item back to 'queued' status.

        Args:
            id_value: Unique ID to reset.
        """
        query = f"""
            UPDATE {self.table_name}
            SET status = 'queued',
                retry_count = 0,
                last_error = NULL,
                last_updated_at = %s
            WHERE {self.id_field} = %s;
        """

        conn = db.get_connection()
        if conn is None:
            logger.error("❌ Could not get DB connection to reset failed item.")
            return

        try:
            with conn.cursor() as cur:
                cur.execute(query, (datetime.utcnow(), id_value))
            conn.commit()
            logger.info("🔄 Reset failed item %s in %s", id_value, self.table_name)
        except Exception as e:
            logger.error(
                "❌ Failed to reset %s in %s: %s", id_value, self.table_name, e
            )
        finally:
            db.release_connection(conn)
