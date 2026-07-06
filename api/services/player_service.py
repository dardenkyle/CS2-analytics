"""
Service layer for retrieving player-related data from the database.
Implements business logic separate from route handlers.
"""

from cs2_analytics.storage.database import Database

from ..schemas.player import PlayerStats


class PlayerService:
    """
    Service class for handling player-related database operations.
    """

    def __init__(self) -> None:
        self.db: Database = Database()

    def fetch_top_players(self, min_maps: int, limit: int) -> list[PlayerStats]:
        """
        Fetches top players based on average rating, filtered by minimum maps played.

        Args:
            min_maps (int): Minimum number of maps a player must have played.
            limit (int): Number of players to return.

        Returns:
            list[PlayerStats]: List of top players with their stats.
        """
        sql: str = """
            SELECT
                player_name,
                COUNT(*) AS maps_played,
                ROUND(AVG(rating)::numeric, 2) AS avg_rating
            FROM players
            GROUP BY player_name
            HAVING COUNT(*) >= %s
            ORDER BY avg_rating DESC
            LIMIT %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(sql, (min_maps, limit))
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                return [PlayerStats(**dict(zip(cols, row))) for row in rows]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch top players: {e}") from e
