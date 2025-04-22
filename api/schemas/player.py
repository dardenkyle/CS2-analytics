"""
Pydantic response models for player-related endpoints in the CS2 Analytics API.
"""

from pydantic import BaseModel


class PlayerStats(BaseModel):
    """
    Response model for top player statistics.
    """

    player_name: str
    maps_played: int
    avg_rating: float
