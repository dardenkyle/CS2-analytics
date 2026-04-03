""" "Module to represent a player in a match."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Player:
    """ "Class to represent a player in a match."""

    map_id: int
    player_id: int
    player_name: str
    player_url: str
    map_name: str
    team_name: str
    kills: int
    headshots: int
    assists: int
    flash_assists: int
    deaths: int
    traded_deaths: int
    opening_kills: int
    opening_deaths: int
    multi_kills: int
    clutches_won: int
    kast: float
    kd_diff: int
    adr: float
    fk_diff: int
    round_swing: float
    rating: float
    last_inserted_at: datetime
    last_scraped_at: datetime
    last_updated_at: datetime
    data_complete: bool

    def to_dict(self) -> dict[str, int | str | bool | float | datetime]:
        """Converts the Player object to a dictionary."""
        return {
            "map_id": self.map_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_url": self.player_url,
            "map_name": self.map_name,
            "team_name": self.team_name,
            "kills": self.kills,
            "headshots": self.headshots,
            "assists": self.assists,
            "flash_assists": self.flash_assists,
            "deaths": self.deaths,
            "traded_deaths": self.traded_deaths,
            "opening_kills": self.opening_kills,
            "opening_deaths": self.opening_deaths,
            "multi_kills": self.multi_kills,
            "clutches_won": self.clutches_won,
            "kast": self.kast,
            "kd_diff": self.kd_diff,
            "adr": self.adr,
            "fk_diff": self.fk_diff,
            "round_swing": self.round_swing,
            "rating": self.rating,
            "last_inserted_at": self.last_inserted_at,
            "last_scraped_at": self.last_scraped_at,
            "last_updated_at": self.last_updated_at,
            "data_complete": self.data_complete,
        }
