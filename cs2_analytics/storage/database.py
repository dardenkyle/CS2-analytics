"""Handles database connections and cursor lifecycle."""

from contextlib import contextmanager

import psycopg2
import psycopg2.pool

from cs2_analytics.config.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from cs2_analytics.exceptions import DatabaseConnectionError, DatabaseOperationError
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

DB_POOL: psycopg2.pool.SimpleConnectionPool | None = None


def _initialize_db_pool() -> psycopg2.pool.SimpleConnectionPool | None:
    """Lazily initializes and returns the shared DB connection pool."""
    global DB_POOL

    if DB_POOL is not None:
        return DB_POOL

    try:
        DB_POOL = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
        )
        logger.info("PostgreSQL connection pool initialized successfully.")
    except (psycopg2.pool.PoolError, psycopg2.Error) as e:
        DB_POOL = None
        raise DatabaseConnectionError(
            "Failed to initialize database connection pool."
        ) from e

    return DB_POOL


class Database:
    """Handles database connection pooling and cursor management."""

    def __init__(self):
        """Initialize the database connection pool."""
        pool = _initialize_db_pool()
        if pool is None:
            raise DatabaseConnectionError("Database connection pool is not available.")
        self.pool = pool

    def get_connection(self):
        """Retrieves a database connection from the pool."""
        try:
            conn = self.pool.getconn()
            logger.debug("Retrieved database connection from pool.")
            return conn
        except (psycopg2.pool.PoolError, psycopg2.Error) as e:
            raise DatabaseConnectionError(
                "Failed to acquire a database connection from the pool."
            ) from e

    def release_connection(self, conn):
        """Releases a database connection back to the pool."""
        if self.pool and conn:
            self.pool.putconn(conn)
            logger.debug("Database connection released back to the pool.")

    def close_db_pool(self):
        """Closes all connections in the database pool."""
        global DB_POOL

        if self.pool:
            self.pool.closeall()
            DB_POOL = None
            logger.info("Database connection pool closed.")

    @contextmanager
    def transaction(self):
        """Yield a cursor whose statements commit or roll back as one unit.

        Unlike get_cursor, callers are expected to run multiple writes on the
        yielded cursor (typically a data write plus an ingestion-state
        transition) before the single commit at exit. Any exception rolls
        back every statement issued on the cursor. See ADR-0013.
        """
        conn = self.get_connection()
        if conn is None:
            raise DatabaseConnectionError(
                "Unable to acquire a database connection from the pool."
            )

        cur = None
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise DatabaseOperationError("Failed during database transaction.") from e
        finally:
            if cur is not None:
                cur.close()
            self.release_connection(conn)

    @contextmanager
    def get_cursor(self):
        """Yield a DB cursor and handle commit, rollback, and connection release."""
        conn = self.get_connection()
        if conn is None:
            raise DatabaseConnectionError(
                "Unable to acquire a database connection from the pool."
            )

        cur = None
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise DatabaseOperationError("Failed during database operation.") from e
        finally:
            if cur is not None:
                cur.close()
            self.release_connection(conn)

    def create_indexes(self) -> bool:
        """Create schema indexes during explicit database setup."""
        conn = self.get_connection()
        if conn is None:
            return False

        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_matches_date ON matches (date);
                CREATE INDEX IF NOT EXISTS idx_maps_match_id ON maps (match_id);
                CREATE INDEX IF NOT EXISTS idx_players_map_id ON players (map_id);
                CREATE INDEX IF NOT EXISTS idx_players_player_id ON players (player_id);
                CREATE INDEX IF NOT EXISTS idx_players_team_name ON players (team_name);
                CREATE INDEX IF NOT EXISTS idx_player_stats ON players (player_id, map_id);
                CREATE INDEX IF NOT EXISTS idx_player_info_team_id ON player_info (team_id);
                CREATE INDEX IF NOT EXISTS idx_player_transfers_player_id
                    ON player_transfers (player_id);
                CREATE INDEX IF NOT EXISTS idx_player_team_history_player_id
                    ON player_team_history (player_id);
                CREATE INDEX IF NOT EXISTS idx_match_ingestion_state_pending
                    ON match_ingestion_state (status, priority DESC, first_seen_at);
                CREATE INDEX IF NOT EXISTS idx_map_ingestion_state_pending
                    ON map_ingestion_state (status, priority DESC, first_seen_at);
                CREATE INDEX IF NOT EXISTS idx_demo_ingestion_state_pending
                    ON demo_ingestion_state (status, priority DESC, first_seen_at);
                """
            )
            conn.commit()
            logger.info("Database indexes created or verified.")
            return True

        except Exception as e:
            raise DatabaseOperationError("Failed to create database indexes.") from e
        finally:
            self.release_connection(conn)
