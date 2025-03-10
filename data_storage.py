import psycopg2
from psycopg2.extras import execute_values
from db_connection import connect_db
from logger_config import setup_logger

logger = setup_logger(__name__)

def batch_insert_matches(match_list: list) -> None:
    """Inserts multiple match records into the database in a single batch operation."""
    if not match_list:
        logger.warning("⚠️ No matches to insert.")
        return

    try:
        conn, cur = connect_db()

        sql = """
        INSERT INTO matches (match_id, match_url, team1, team2, score1, score2, event, date)
        VALUES %s
        ON CONFLICT (match_url) DO NOTHING
        RETURNING match_id;
        """

        execute_values(cur, sql, match_list)
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"✅ Successfully inserted {len(match_list)} matches.")

    except Exception as e:
        logger.error(f"❌ Error inserting matches: {e}")

def batch_insert_player_stats(player_stats_list: list) -> None:
    """Inserts multiple player stats records in a single batch operation."""
    if not player_stats_list:
        logger.warning("⚠️ No player stats to insert.")
        return

    try:
        conn, cur = connect_db()

        sql = """
        INSERT INTO player_stats 
        (match_id, player_name, kills, headshots, assists, flash_assists, deaths, kast, kd_diff, fk_diff, adr, rating)
        VALUES %s;
        """

        execute_values(cur, sql, player_stats_list)
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"✅ Successfully inserted {len(player_stats_list)} player stats.")

    except Exception as e:
        logger.error(f"❌ Error inserting player stats: {e}")