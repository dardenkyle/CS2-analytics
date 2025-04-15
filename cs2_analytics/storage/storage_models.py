class Match:
    """Represents a CS2 match with structured attributes."""
    
    def __init__(self, match_id, match_url, map_stats_links, team1, team2, score1, score2, event, match_type, forfeit, date, data_complete):
        self.match_id = match_id
        self.match_url = match_url
        self.map_stats_links = map_stats_links  # List of URLs to map stats pages
        self.team1 = team1
        self.team2 = team2
        self.score1 = score1
        self.score2 = score2
        self.event = event
        self.match_type = match_type
        self.forfeit = forfeit
        self.date = date
        self.data_complete = data_complete

    def to_dict(self):
        """Converts the object to a dictionary for database insertion."""
        return {
            "match_id": self.match_id,
            "match_url": self.match_url,
            "map_stats_links": self.map_stats_links,  # Ensure this is converted correctly for DB
            "team1": self.team1,
            "team2": self.team2,
            "score1": self.score1,
            "score2": self.score2,
            "event": self.event,
            "match_type": self.match_type,
            "forfeit": self.forfeit,
            "date": self.date,
            "data_complete": self.data_complete
        }


class Player:
    """Represents an individual player's statistics."""
    
    def __init__(self, map_id, player_id, player_name, player_url, map_name, team_name, kills, headshots, assists, flash_assists, deaths, kast, kd_diff, adr, fk_diff, rating, data_complete):
        self.map_id = map_id
        self.player_id = player_id
        self.player_name = player_name
        self.player_url = player_url
        self.map_name = map_name
        self.team_name = team_name
        self.kills = kills
        self.headshots = headshots
        self.assists = assists
        self.flash_assists = flash_assists
        self.deaths = deaths
        self.kast = kast
        self.kd_diff = kd_diff
        self.adr = adr
        self.fk_diff = fk_diff
        self.rating = rating
        self.data_complete = data_complete

    def to_dict(self):
        """Converts the object to a dictionary for database insertion."""
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
            "kast": self.kast,
            "kd_diff": self.kd_diff,
            "adr": self.adr,
            "fk_diff": self.fk_diff,
            "rating": self.rating,
            "data_complete": self.data_complete
        }
