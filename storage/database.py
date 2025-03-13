import psycopg2
import psycopg2.pool
from config.config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
from log_manager.logger_config import setup_logger

logger = setup_logger(__name__)

# ✅ Initialize connection pool
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,  # ✅ Adjust based on expected load
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    logger.info("✅ PostgreSQL connection pool initialized successfully.")
except Exception as e:
    logger.error(f"❌ Failed to initialize database connection pool: {e}")
    db_pool = None

class Database:
    """Handles all database interactions, including connection management and data storage."""

    def __init__(self):
        """Initialize database connection."""
        if db_pool is None:
            raise Exception("❌ Database connection pool is not available.")

        self.create_indexes() # Automatically ensure indexes exist

    def get_connection(self):
        """Retrieves a database connection from the pool."""
        try:
            conn = db_pool.getconn()
            logger.debug("✅ Retrieved database connection from pool.")
            return conn
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            return None

    def release_connection(self, conn):
        """Releases a database connection back to the pool."""
        if db_pool and conn:
            db_pool.putconn(conn)
            logger.debug("🔄 Database connection released back to the pool.")

    def close_db_pool(self):
        """Closes all connections in the database pool."""
        if db_pool:
            db_pool.closeall()
            logger.info("❌ Database connection pool closed.")

    def store_matches(self, match_data):
        """Stores match data with upsert logic."""
        conn = self.get_connection()
        if conn is None:
            return

        try:
            cur = conn.cursor()
            query = """
                INSERT INTO matches (match_id, match_url, map_stats_links, team1, team2, score1, score2, event, match_type, forfeit, date, data_complete)
                VALUES (%(match_id)s, %(match_url)s, %(map_stats_links)s, %(team1)s, %(team2)s, %(score1)s, %(score2)s, %(event)s, %(match_type)s, %(forfeit)s, %(date)s, %(data_complete)s)
                ON CONFLICT (match_id) DO UPDATE 
                SET 
                    score1 = EXCLUDED.score1,
                    score2 = EXCLUDED.score2,
                    event = EXCLUDED.event,
                    data_complete = EXCLUDED.data_complete;
            """

            cur.executemany(query, match_data)
            conn.commit()
            logger.info(f"✅ Stored {len(match_data)} matches successfully.")

        except Exception as e:
            logger.error(f"❌ Error storing match data: {e}")
        finally:
            self.release_connection(conn)

    def store_players(self, player_stats):
        """Stores player statistics with upsert logic."""
        conn = self.get_connection()
        if conn is None:
            return

        try:
            # ✅ Ensure player_stats are dictionaries before inserting
            formatted_data = [p.to_dict() if hasattr(p, 'to_dict') else p for p in player_stats]

            cur = conn.cursor()
            query = """
                INSERT INTO players (game_id, player_id, player_name, player_url, map_name, team_name, kills, headshots, assists, flash_assists, deaths, kast, kd_diff, adr, fk_diff, rating, data_complete)
                VALUES (%(game_id)s, %(player_id)s, %(player_name)s, %(player_url)s, %(map_name)s, %(team_name)s, %(kills)s, %(headshots)s, %(assists)s, %(flash_assists)s, %(deaths)s, %(kast)s, %(kd_diff)s, %(adr)s, %(fk_diff)s, %(rating)s, %(data_complete)s)
                ON CONFLICT (game_id, player_id) DO UPDATE 
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
            logger.info(f"✅ Stored {len(player_stats)} players successfully.")

        except Exception as e:
            logger.error(f"❌ Error storing player stats: {e}")
        finally:
            self.release_connection(conn)

    def create_indexes(self):
        """Ensures necessary indexes exist for optimized queries."""
        conn = self.get_connection()
        if conn is None:
            return

        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_matches_date ON matches (date);
                CREATE INDEX IF NOT EXISTS idx_players_game_id ON players (game_id);
                CREATE INDEX IF NOT EXISTS idx_players_team_name ON players (team_name);
                CREATE INDEX IF NOT EXISTS idx_player_stats ON players (player_id, game_id);
            """)
            conn.commit()
            logger.info("✅ Database indexes ensured.")

        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")
        finally:
            self.release_connection(conn)
