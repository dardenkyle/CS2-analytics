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
        Fetches top players by average rating, filtered by minimum rated maps.

        Reads the dbt-built `analytics.agg_player_ratings` mart, which holds
        one row per player with the exact, unrounded average, so each request
        is an ordered read rather than an aggregation over every player-map
        row. The floor applies to `rated_maps`, the maps the average is
        computed from, so maps without a rating cannot carry a player over it.
        Ordering uses the unrounded average, then maps played, then
        player_id, so ties resolve the same way on every build; the average
        is rounded to two decimals only for the response. The ORDER BY
        qualifies `agg_player_ratings.avg_rating` because a bare name binds
        to the rounded output column. Players whose ratings are all null
        are excluded.

        Args:
            min_maps (int): Minimum number of rated maps a player must have.
            limit (int): Number of players to return.

        Returns:
            list[PlayerStats]: List of top players with their stats.
        """
        sql: str = """
            SELECT
                player_id,
                player_name,
                maps_played,
                ROUND(avg_rating::numeric, 2) AS avg_rating
            FROM analytics.agg_player_ratings
            WHERE rated_maps >= %s
                AND avg_rating IS NOT NULL
            ORDER BY agg_player_ratings.avg_rating DESC, maps_played DESC, player_id
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
