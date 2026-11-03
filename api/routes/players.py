"""
Route definitions related to player data for the CS2 Analytics API.
"""

from fastapi import APIRouter, Query, Response

from ..schemas.player import PlayerStats
from ..services.player_service import PlayerService

router: APIRouter = APIRouter()

# The marts behind this endpoint change once a day with the scheduled dbt
# build, so a short public cache spares repeat reads without serving a
# stale ranking for long after a build.
TOP_PLAYERS_CACHE_SECONDS = 300


@router.get("/top_players", response_model=list[PlayerStats])
def get_top_players(
    response: Response,
    min_maps: int = Query(5, ge=1),
    limit: int = Query(10, le=100),
) -> list[PlayerStats]:
    """
    Returns the top CS2 players by average rating, filtered by minimum maps played.

    Successful responses carry a short public `Cache-Control` header; error
    responses do not.
    """
    service = PlayerService()
    players = service.fetch_top_players(min_maps=min_maps, limit=limit)
    response.headers["Cache-Control"] = f"public, max-age={TOP_PLAYERS_CACHE_SECONDS}"
    return players
