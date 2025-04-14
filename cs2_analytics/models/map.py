"""This module contains the Map class, which is used to represent a single map in a match."""

from dataclasses import dataclass


@dataclass
class Map:
    """A class used to represent a single map in a match."""

    game_id: int
    match_id: int
    map_name: str
    map_order: int
    team1_score: int
    team2_score: int
    winner: str
    date: str
    data_complete: bool

    def to_dict(self):
        """ "Converts the object to a dictionary for database insertion."""
        return {
            "game_id": self.game_id,
            "match_id": self.match_id,
            "map_name": self.map_name,
            "map_order": self.map_order,
            "team1_score": self.team1_score,
            "team2_score": self.team2_score,
            "winner": self.winner,
            "date": self.date,
            "data_complete": self.data_complete,
        }
