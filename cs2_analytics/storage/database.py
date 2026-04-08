"""Handles all database interactions, including connection management and data storage."""

from contextlib import contextmanager

import psycopg2
import psycopg2.pool

from cs2_analytics.config.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
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
        logger.info("✅ PostgreSQL connection pool initialized successfully.")
    except (psycopg2.pool.PoolError, psycopg2.Error) as e:
        DB_POOL = None
        raise ConnectionError("Failed to initialize database connection pool.") from e

    return DB_POOL


class Database:
    """Handles all database interactions, including connection management and data storage."""

    _indexes_ensured = False

    def __init__(self):
        """Initialize database connection."""
        self.pool = _initialize_db_pool()
        if self.pool is None:
            raise ConnectionError("Database connection pool is not available.")

        if not Database._indexes_ensured:
            Database._indexes_ensured = self.create_indexes()

    def get_connection(self):
        """Retrieves a database connection from the pool."""
        try:
            conn = self.pool.getconn()
            logger.debug("✅ Retrieved database connection from pool.")
            return conn
        except (psycopg2.pool.PoolError, psycopg2.Error) as e:
            raise ConnectionError(
                "Failed to acquire a database connection from the pool."
            ) from e

    def release_connection(self, conn):
        """Releases a database connection back to the pool."""
        if self.pool and conn:
            self.pool.putconn(conn)
            logger.debug("🔄 Database connection released back to the pool.")

    def close_db_pool(self):
        """Closes all connections in the database pool."""
        global DB_POOL

        if self.pool:
            self.pool.closeall()
            DB_POOL = None
            logger.info("❌ Database connection pool closed.")

    @contextmanager
    def get_cursor(self):
        """Yields a DB cursor and handles commit/rollback and connection release."""
        conn = self.get_connection()
        if conn is None:
            raise ConnectionError(
                "Unable to acquire a database connection from the pool."
            )

        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.release_connection(conn)

    def create_indexes(self) -> bool:
        """Ensures necessary indexes exist for optimized queries."""
        conn = self.get_connection()
        if conn is None:
            return False

        try:
            cur = conn.cursor()
            cur.execute(
                """
                ALTER TABLE players ADD COLUMN IF NOT EXISTS traded_deaths INT;
                ALTER TABLE players ADD COLUMN IF NOT EXISTS opening_kills INT;
                ALTER TABLE players ADD COLUMN IF NOT EXISTS opening_deaths INT;
                ALTER TABLE players ADD COLUMN IF NOT EXISTS multi_kills INT;
                ALTER TABLE players ADD COLUMN IF NOT EXISTS clutches_won INT;
                ALTER TABLE players ADD COLUMN IF NOT EXISTS round_swing FLOAT;

                CREATE INDEX IF NOT EXISTS idx_matches_date ON matches (date);
                CREATE INDEX IF NOT EXISTS idx_players_map_id ON players (map_id);
                CREATE INDEX IF NOT EXISTS idx_players_team_name ON players (team_name);
                CREATE INDEX IF NOT EXISTS idx_player_stats ON players (player_id, map_id);
            """
            )
            conn.commit()
            logger.info("✅ Database indexes ensured.")
            return True

        except Exception as e:
            raise RuntimeError("Failed to create database indexes.") from e
        finally:
            self.release_connection(conn)



