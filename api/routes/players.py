"""
Route definitions related to player data for the CS2 Analytics API.
"""

from fastapi import APIRouter, Query
from cs2_analytics.api.schemas.player import PlayerStats
from cs2_analytics.api.services.player_service import PlayerService


router: APIRouter = APIRouter()


@router.get("/top_players", response_model=list[PlayerStats])
def get_top_players(
    min_maps: int = Query(5, ge=1), limit: int = Query(10, le=100)
) -> list[PlayerStats]:
    """
    Returns the top CS2 players by average rating, filtered by minimum maps played.
    """
    service = PlayerService()
    return service.fetch_top_players(min_maps=min_maps, limit=limit)
