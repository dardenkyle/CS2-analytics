"""This module contains the Map class, which is used to represent a single map in a match."""

from dataclasses import dataclass
from datetime import datetime

type MapDictValue = int | str | bool | datetime


@dataclass
class Map:
    """A class used to represent a single map in a match."""

    map_id: int
    match_id: int
    map_url: str
    map_name: str
    map_order: int
    team1_score: int
    team2_score: int
    map_winner: str
    date: str
    inserted_at: datetime
    last_scraped_at: datetime
    last_updated_at: datetime
    data_complete: bool

    def to_dict(self) -> dict[str, MapDictValue]:
        """ "Converts the object to a dictionary for database insertion."""
        return {
            "map_id": self.map_id,
            "match_id": self.match_id,
            "map_url": self.map_url,
            "map_name": self.map_name,
            "map_order": self.map_order,
            "team1_score": self.team1_score,
            "team2_score": self.team2_score,
            "map_winner": self.map_winner,
            "date": self.date,
            "inserted_at": self.inserted_at,
            "last_scraped_at": self.last_scraped_at,
            "last_updated_at": self.last_updated_at,
            "data_complete": self.data_complete,
        }
