import psycopg2
from psycopg2.extras import execute_values
from storage.db_connection import connect_db
from log_manager.logger_config import setup_logger

logger = setup_logger(__name__)

class DataManager:
    """Handles database interactions for match and player data."""

    def __init__(self):
        """Ensures tables are set up before any data operations."""
        self.conn = connect_db()
        self.cur = self.conn.cursor()

    def store_match_data(self, match_list: list[tuple]) -> None:
        """Stores match data in the database while preventing duplicates."""
        if not match_list:
            logger.warning("⚠️ No matches to insert.")
            return

        sql = """
        INSERT INTO matches (match_id, match_url, team1, team2, score1, score2, event, date)
        VALUES %s
        ON CONFLICT (match_url) DO NOTHING;  -- ✅ Prevents duplicate match inserts
        """

        try:
            execute_values(self.cur, sql, match_list)
            self.conn.commit()
            logger.info(f"✅ Inserted {len(match_list)} new matches.")
        except Exception as e:
            self.conn.rollback()  # Roll back transaction in case of failure
            logger.error(f"❌ Error inserting match data: {e}")
        finally:
            self.close_connection()

    def store_player_data(self, player_stats_list: list[tuple]) -> None:
        """Stores player statistics in the database while preventing duplicates."""
        if not player_stats_list:
            logger.warning("⚠️ No player stats to insert.")
            return

        sql = """
        INSERT INTO player_stats (match_id, player_name, kills, headshots, assists, flash_assists, deaths, kast, kd_diff, adr, fk_diff, rating)
        VALUES %s
        ON CONFLICT (match_id, player_name) DO NOTHING;  -- ✅ Ensures only new player stats are added
        """

        try:
            execute_values(self.cur, sql, player_stats_list)
            self.conn.commit()
            logger.info(f"✅ Inserted {len(player_stats_list)} new player stats.")
        except Exception as e:
            self.conn.rollback()  # Roll back transaction in case of failure
            logger.error(f"❌ Error inserting player stats: {e}")
        finally:
            self.close_connection()

    def close_connection(self):
        """Closes database connection safely."""
        try:
            self.cur.close()
            self.conn.close()
        except Exception as e:
            logger.error(f"❌ Error closing database connection: {e}")

