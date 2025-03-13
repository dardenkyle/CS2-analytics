import psycopg2
import psycopg2.extras
from storage.db_connection import connect_db, release_db_connection
from config.config import BATCH_SIZE
from log_manager.logger_config import setup_logger

logger = setup_logger(__name__)

class DataManager:
    """Handles storing match, map, and player data in PostgreSQL."""

    def __init__(self):
        self.conn = connect_db()
        if self.conn:
            self.cur = self.conn.cursor()
        else:
            self.cur = None

    def store_match_data(self, match_list):
        """Inserts match data into the database in batches."""
        if not match_list:
            logger.warning("⚠️ No match data to insert.")
            return
        
        query = """
        INSERT INTO matches (match_id, match_url, map_stats_links, team1, team2, score1, score2, event, match_type, forfeit, date, data_complete)
        VALUES %s
        ON CONFLICT (match_id) DO UPDATE 
        SET score1 = EXCLUDED.score1, score2 = EXCLUDED.score2, data_complete = EXCLUDED.data_complete;
        """
        
        try:
            conn = connect_db()
            if conn is None:
                return

            cur = conn.cursor()

            # ✅ Correct usage of execute_values() for batch insert
            psycopg2.extras.execute_values(cur, query, match_list)

            conn.commit()
            cur.close()
            release_db_connection(conn)

            logger.info(f"✅ Successfully stored {len(match_list)} matches.")

        except Exception as e:
            logger.error(f"❌ Database insert error: {e}")

    def store_map_data(self, map_list):
        """Inserts map data into the database in batches."""
        if not map_list:
            logger.warning("⚠️ No map data to insert.")
            return
        
        query = """
        INSERT INTO maps (game_id, match_id, map_name, map_order, team1_score, team2_score, winner, date, data_complete)
        VALUES %s
        ON CONFLICT (game_id) DO NOTHING;
        """
        
        self._batch_insert(query, map_list)

    def store_player_data(self, player_list):
        """Inserts player stats into the database in batches."""
        if not player_list:
            logger.warning("⚠️ No player data to insert.")
            return
        
        query = """
        INSERT INTO players (game_id, player_id, player_name, player_url, map_name, team_name, kills, headshots, assists, flash_assists, deaths, kast, kd_diff, adr, fk_diff, rating, data_complete)
        VALUES %s
        ON CONFLICT (game_id, player_id) DO UPDATE 
        SET kills = EXCLUDED.kills, deaths = EXCLUDED.deaths, kast = EXCLUDED.kast, rating = EXCLUDED.rating;
        """
        
        self._batch_insert(query, player_list)

    def _batch_insert(self, query, data_list):
        """Handles batch inserting data for performance."""
        try:
            for i in range(0, len(data_list), BATCH_SIZE):
                batch = data_list[i:i + BATCH_SIZE]
                psycopg2.extras.execute_values(self.cur, query, batch)       # Issue with batch_insert ?? maybe
                self.conn.commit()
                logger.info(f"✅ Inserted {len(batch)} rows.")
        except Exception as e:
            logger.error(f"❌ Database insert error: {e}")
            self.conn.rollback()

    def close(self):
        """Closes database connection."""
        if self.cur:
            self.cur.close()
        release_db_connection(self.conn)
