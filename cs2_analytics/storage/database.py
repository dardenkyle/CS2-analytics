"""Handles all database interactions, including connection management and data storage."""

import psycopg2
import psycopg2.pool
from contextlib import contextmanager
from cs2_analytics.config.config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

# ✅ Initialize connection pool
try:
    DB_POOL = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,  # ✅ Adjust based on expected load
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
    )
    logger.info("✅ PostgreSQL connection pool initialized successfully.")
except ConnectionError as e:
    logger.error("❌ Failed to initialize database connection pool: %s", e)
    DB_POOL = None


class Database:
    """Handles all database interactions, including connection management and data storage."""

    def __init__(self):
        """Initialize database connection."""
        if DB_POOL is None:
            raise ConnectionError("Database connection pool is not available.")

        self.create_indexes()  # Automatically ensure indexes exist

    def get_connection(self):
        """Retrieves a database connection from the pool."""
        try:
            conn = DB_POOL.getconn()
            logger.debug("✅ Retrieved database connection from pool.")
            return conn
        except ConnectionError as e:
            logger.error("Database connection error: %s", e)
            return None

    def release_connection(self, conn):
        """Releases a database connection back to the pool."""
        if DB_POOL and conn:
            DB_POOL.putconn(conn)
            logger.debug("🔄 Database connection released back to the pool.")

    def close_db_pool(self):
        """Closes all connections in the database pool."""
        if DB_POOL:
            DB_POOL.closeall()
            logger.info("❌ Database connection pool closed.")

    @contextmanager
    def get_cursor(self):
        """Yields a DB cursor and handles commit/rollback and connection release."""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("❌ Error during DB operation: %s", e)
            raise
        finally:
            self.release_connection(conn)


    def store_matches(self, match_data):
        """Stores match data with upsert logic."""
        conn = self.get_connection()
        if conn is None:
            return

        try:
            cur = conn.cursor()
            query = """
                INSERT INTO matches (match_id, match_url, map_links, demo_links, team1, team2, score1, score2, winner, event, match_type, forfeit, date, last_inserted_at, last_scraped_at, last_updated_at, data_complete)
                VALUES (%(match_id)s, %(match_url)s, %(map_links)s, %(demo_links)s, %(team1)s, %(team2)s, %(score1)s, %(score2)s, %(winner)s, %(event)s, %(match_type)s, %(forfeit)s, %(date)s, %(last_inserted_at)s, %(last_scraped_at)s, %(last_updated_at)s, %(data_complete)s)
                ON CONFLICT (match_id) DO UPDATE 
                SET 
                    score1 = EXCLUDED.score1,
                    score2 = EXCLUDED.score2,
                    event = EXCLUDED.event,
                    data_complete = EXCLUDED.data_complete;
            """

            cur.executemany(query, match_data)
            conn.commit()
            logger.info("Stored %s matches successfully.", len(match_data))

        except Exception as e:
            logger.error("Error storing match data: %s", e)
        finally:
            self.release_connection(conn)

    def store_players(self, player_stats):
        """Stores player statistics with upsert logic."""
        conn = self.get_connection()
        if conn is None:
            return

        try:
            # ✅ Ensure player_stats are dictionaries before inserting
            formatted_data = [
                p.to_dict() if hasattr(p, "to_dict") else p for p in player_stats
            ]

            cur = conn.cursor()
            query = """
                INSERT INTO players (match_id, map_id, player_id, player_name, player_url, map_name, team_name, kills, headshots, assists, flash_assists, deaths, kast, kd_diff, adr, fk_diff, rating, data_complete)
                VALUES (%(match_id)s, %(map_id)s, %(player_id)s, %(player_name)s, %(player_url)s, %(map_name)s, %(team_name)s, %(kills)s, %(headshots)s, %(assists)s, %(flash_assists)s, %(deaths)s, %(kast)s, %(kd_diff)s, %(adr)s, %(fk_diff)s, %(rating)s, %(data_complete)s)
                ON CONFLICT (map_id, player_id) DO UPDATE 
                SET 
                    kills = EXCLUDED.kills,
                    headshots = EXCLUDED.headshots,
                    assists = EXCLUDED.assists,
                    deaths = EXCLUDED.deaths,
                    kast = EXCLUDED.kast,
                    rating = EXCLUDED.rating,
                    data_complete = EXCLUDED.data_complete;
            """

            cur.executemany(query, formatted_data)
            conn.commit()
            logger.info("Stored %s players successfully.", len(player_stats))

        except Exception as e:
            logger.error("Error storing player stats: %s", e)
        finally:
            self.release_connection(conn)

    def create_indexes(self):
        """Ensures necessary indexes exist for optimized queries."""
        conn = self.get_connection()
        if conn is None:
            return

        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_matches_date ON matches (date);
                CREATE INDEX IF NOT EXISTS idx_players_map_id ON players (map_id);
                CREATE INDEX IF NOT EXISTS idx_players_team_name ON players (team_name);
                CREATE INDEX IF NOT EXISTS idx_player_stats ON players (player_id, map_id);
            """
            )
            conn.commit()
            logger.info("✅ Database indexes ensured.")

        except Exception as e:
            logger.error("Error creating indexes: %s", e)
        finally:
            self.release_connection(conn)
