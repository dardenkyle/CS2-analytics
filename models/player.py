from dataclasses import dataclass


@dataclass
class Player:
    game_id: int
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
    kast: float
    kd_diff: int
    adr: float
    fk_diff: int
    rating: float
    data_complete: bool

    def to_dict(self):
        return {
            "match_id": self.match_id,
            "match_url": self.match_url,
            "map_stats_links": self.map_stats_links,
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
