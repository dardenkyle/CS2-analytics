"""
Provides a base class for managing scrape queues used to track scraping progress
of matches, maps, and demo files. Subclasses configure their specific table names
and primary identifier fields while reusing shared logic for insert, update, and
fetch operations.
"""

from abc import ABC
from datetime import datetime
from typing import List, Tuple, Optional
from storage import db  # Assumes `db = Database()` is defined in `storage/__init__.py`


class BaseScrapeQueue(ABC):
    """
    Abstract base class for all scrape queue managers.

    Encapsulates common database operations for queue management:
    inserting new tasks, fetching queued items, marking them as
    parsed or failed, and resetting failed jobs.
    """

    def __init__(self, table_name: str, id_field: str) -> None:
        """
        Initialize the queue with a table name and its primary ID field.

        Args:
            table_name (str): The name of the table representing the queue.
            id_field (str): The primary identifier column for the queue (e.g., 'match_id').
        """
        self.table_name = table_name
        self.id_field = id_field

    def queue(
        self, id_value: str, url: str, source: str = "", priority: int = 0
    ) -> None:
        """
        Inserts a new scrape task into the queue table if it does not already exist.

        Args:
            id_value (str): Unique identifier for the queued item.
            url (str): URL associated with the task.
            source (str): Optional label indicating where the task was discovered.
            priority (int): Optional priority score (higher values are processed first).
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
        conn = db.get_connection()
        if conn is None:
            return

        try:
            with conn.cursor() as cur:
                cur.execute(query, (id_value, url, now, now, priority, source))
            conn.commit()
        except Exception as e:
            print(f"❌ Failed to queue '{id_value}' in '{self.table_name}': {e}")
        finally:
            db.release_connection(conn)

    def fetch(self, limit: int = 50) -> List[Tuple[str, str]]:
        """
        Fetches a list of queued tasks for processing.

        Args:
            limit (int): Maximum number of items to return. Defaults to 50.

        Returns:
            List of (id, url) tuples representing tasks ready for processing.
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
            return []

        try:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                return cur.fetchall()
        except Exception as e:
            print(f"❌ Failed to fetch from '{self.table_name}': {e}")
            return []
        finally:
            db.release_connection(conn)

    def mark_parsed(self, id_value: str) -> None:
        """
        Marks a task as successfully parsed.

        Args:
            id_value (str): Unique identifier for the task being marked complete.
        """
        query = f"""
            UPDATE {self.table_name}
            SET status = 'parsed', last_updated_at = %s
            WHERE {self.id_field} = %s;
        """
        conn = db.get_connection()
        if conn is None:
            return

        try:
            with conn.cursor() as cur:
                cur.execute(query, (datetime.utcnow(), id_value))
            conn.commit()
        except Exception as e:
            print(
                f"❌ Failed to mark '{id_value}' as parsed in '{self.table_name}': {e}"
            )
        finally:
            db.release_connection(conn)

    def mark_failed(self, id_value: str, error_msg: Optional[str] = "") -> None:
        """
        Marks a task as failed, increments retry count, and stores the error message.

        Args:
            id_value (str): Unique identifier of the failed task.
            error_msg (str): Optional error description (truncated to 500 chars).
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
            return

        try:
            with conn.cursor() as cur:
                cur.execute(query, (datetime.utcnow(), error_msg[:500], id_value))
            conn.commit()
        except Exception as e:
            print(
                f"❌ Failed to mark '{id_value}' as failed in '{self.table_name}': {e}"
            )
        finally:
            db.release_connection(conn)

    def reset_failed(self, id_value: str) -> None:
        """
        Resets a failed task to 'queued' status and clears retry count and error info.

        Args:
            id_value (str): Unique identifier of the task to reset.
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
            return

        try:
            with conn.cursor() as cur:
                cur.execute(query, (datetime.utcnow(), id_value))
            conn.commit()
        except Exception as e:
            print(f"❌ Failed to reset '{id_value}' in '{self.table_name}': {e}")
        finally:
            db.release_connection(conn)
