from dataclasses import dataclass, field
from typing import List, Optional
from models.player import Player


@dataclass
class Match:
    match_id: int
    match_url: str
    map_links: List[str]
    team1: str
    team2: str
    score1: int
    score2: int
    event: str
    match_type: str
    forfeit: bool
    date: str
    data_complete: bool

    def to_dict(self):
        return {
            "match_id": self.match_id,
            "match_url": self.match_url,
            "map_links": self.map_links,
            "team1": self.team1,
            "team2": self.team2,
            "score1": self.score1,
            "score2": self.score2,
            "event": self.event,
            "match_type": self.match_type,
            "forfeit": self.forfeit,
            "date": self.date,
            "data_complete": self.data_complete,
        }
