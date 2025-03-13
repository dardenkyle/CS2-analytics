import psycopg2
import psycopg2.pool
from config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
from utils.log_manager import get_logger
from storage.models import Player, Match

class Database:
    """Handles database connections and manages match & player data storage."""

    _db_pool = None  # Singleton connection pool

    def __init__(self, minconn=1, maxconn=10):
        """Initializes the database connection pool."""
        self.logger = get_logger(self.__class__.__name__)

        if Database._db_pool is None:
            try:
                Database._db_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=minconn,
                    maxconn=maxconn,
                    dbname=DB_NAME,
                    user=DB_USER,
                    password=DB_PASS,
                    host=DB_HOST,
                    port=DB_PORT
                )
                self.logger.info("✅ PostgreSQL connection pool initialized successfully.")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize database connection pool: {e}")
                Database._db_pool = None

    def get_connection(self):
        """Retrieves a database connection from the pool."""
        if Database._db_pool is None:
            self.logger.error("❌ Database connection pool is not available.")
            return None
        try:
            conn = Database._db_pool.getconn()
            self.logger.info("✅ Successfully retrieved a database connection.")
            return conn
        except Exception as e:
            self.logger.error(f"❌ Database connection error: {e}")
            return None

    def release_connection(self, conn):
        """Releases a database connection back to the pool."""
        if Database._db_pool and conn:
            Database._db_pool.putconn(conn)
            self.logger.info("🔄 Database connection released back to the pool.")

    @classmethod
    def close_pool(cls):
        """Closes all connections in the database pool."""
        if cls._db_pool:
            cls._db_pool.closeall()
            cls._db_pool = None
            get_logger(cls.__name__).info("❌ Database connection pool closed.")

    def store_matches(self, matches):
        """Stores match data in the database."""
        conn = self.get_connection()
        if conn is None:
            return

        try:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO matches (match_id, match_url, map_stats_links, team1, team2, score1, score2, event, match_type, forfeit, date, data_complete)
                VALUES (%(match_id)s, %(match_url)s, %(map_stats_links)s, %(team1)s, %(team2)s, %(score1)s, %(score2)s, %(event)s, %(match_type)s, %(forfeit)s, %(date)s, %(data_complete)s)
                ON CONFLICT (match_id) DO NOTHING;
            """, [match.to_dict() for match in matches])
            conn.commit()
            self.logger.info(f"✅ Stored {len(matches)} matches successfully.")

        except Exception as e:
            self.logger.error(f"❌ Error storing matches: {e}")

        finally:
            self.release_connection(conn)

    def store_players(self, player_stats):
        """Stores player statistics in the database."""
        conn = self.get_connection()
        if conn is None:
            return

        try:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO players (game_id, player_id, player_name, player_url, map_name, team_name, kills, headshots, assists, flash_assists, deaths, kast, kd_diff, adr, fk_diff, rating, data_complete)
                VALUES (%(game_id)s, %(player_id)s, %(player_name)s, %(player_url)s, %(map_name)s, %(team_name)s, %(kills)s, %(headshots)s, %(assists)s, %(flash_assists)s, %(deaths)s, %(kast)s, %(kd_diff)s, %(adr)s, %(fk_diff)s, %(rating)s, %(data_complete)s)
                ON CONFLICT (game_id, player_id) DO NOTHING;
            """, [player.to_dict() for player in player_stats])
            conn.commit()
            self.logger.info(f"✅ Stored {len(player_stats)} player stats successfully.")

        except Exception as e:
            self.logger.error(f"❌ Error storing player stats: {e}")

        finally:
            self.release_connection(conn)

