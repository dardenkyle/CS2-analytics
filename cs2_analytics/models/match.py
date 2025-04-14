"""This module defines the Match class, which represents a match in the system."""

from datetime import datetime
from dataclasses import dataclass
from typing import List


@dataclass
class Match:
    """Represents a match in the system."""

    match_id: int
    match_url: str
    map_links: List[str]
    demo_links: List[str]
    team1: str
    team2: str
    score1: int
    score2: int
    winner: str
    event: str
    match_type: str
    forfeit: bool
    date: str
    last_inserted_at: datetime
    last_scraped_at: datetime
    last_updated_at: datetime
    data_complete: bool

    def to_dict(self):
        """Converts match object to a dictionary."""
        return {
            "match_id": self.match_id,
            "match_url": self.match_url,
            "map_links": self.map_links,
            "demo_links": self.demo_links,
            "team1": self.team1,
            "team2": self.team2,
            "score1": self.score1,
            "score2": self.score2,
            "winner": self.winner,
            "event": self.event,
            "match_type": self.match_type,
            "forfeit": self.forfeit,
            "date": self.date,
            "last_inserted_at": self.last_inserted_at,
            "last_scraped_at": self.last_scraped_at,
            "last_updated_at": self.last_updated_at,
            "data_complete": self.data_complete,
        }
