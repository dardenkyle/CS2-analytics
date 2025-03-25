import time
import random
from bs4 import BeautifulSoup
from utils import get_logger
from models import Player
from seleniumbase import Driver

# from seleniumbase import Driver

logger = get_logger(__name__)


class MapParser:

    def __init__(self):
        self.driver = Driver(uc=True, headless=True)

    def extract_player_stats(
        self, map_url: str, match_id: int, map_name: str = None
    ) -> list[Player]:
        """Extracts player object from a map stats page."""
        self.driver.get(map_url)
        time.sleep(random.uniform(3, 5))
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        players = []
        try:
            tables = soup.find_all("table", class_="stats-table")
            for table in tables:
                team_header = table.find_previous("div", class_="teamName")
                team_name = team_header.text.strip() if team_header else "Unknown"

                rows = table.find_all("tr", class_="")  # Skips header row
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) < 10:
                        continue

                    player_link = cols[0].find("a")
                    player_url = (
                        f"https://www.hltv.org{player_link['href']}"
                        if player_link
                        else ""
                    )
                    player_id = (
                        int(player_link["href"].split("/")[2]) if player_link else -1
                    )
                    player_name = (
                        player_link.text.strip()
                        if player_link
                        else cols[0].text.strip()
                    )

                    player = Player(
                        game_id=match_id,
                        player_id=player_id,
                        player_name=player_name,
                        player_url=player_url,
                        map_name=map_name or "unknown",
                        team_name=team_name,
                        kills=int(cols[1].text.strip()),
                        headshots=int(cols[3].text.strip()),
                        assists=int(cols[2].text.strip()),
                        flash_assists=int(cols[6].text.strip()),
                        deaths=int(
                            cols[2].text.strip()
                        ),  # may want to adjust if deaths are in different col
                        kast=float(cols[5].text.strip().replace("%", "")) / 100,
                        kd_diff=int(cols[7].text.strip()),
                        adr=float(cols[4].text.strip()),
                        fk_diff=int(cols[8].text.strip()),
                        rating=float(cols[9].text.strip()),
                        data_complete=True,
                    )

                    players.append(player)

                    player_data = {
                        "game_id": match_id,
                        "player_id": None,  # Replace this if you parse the player URL
                        "player_name": cols[0].text.strip(),
                        "player_url": None,  # Replace if available
                        "map_name": None,  # Replace if you parse map name from `map_url`
                        "team_name": team_name,
                        "kills": int(cols[1].text.strip()),
                        "headshots": int(cols[3].text.strip()),
                        "assists": int(cols[2].text.strip()),
                        "flash_assists": int(cols[6].text.strip()),
                        "deaths": int(cols[2].text.strip()),
                        "kast": float(cols[5].text.strip().replace("%", "")) / 100,
                        "kd_diff": int(cols[7].text.strip()),
                        "adr": float(cols[4].text.strip()),
                        "fk_diff": int(cols[8].text.strip()),
                        "rating": float(cols[9].text.strip()),
                        "data_complete": True,
                    }
                    players.append(player_data)
        except Exception as e:
            logger.error(f"❌ Failed to extract player stats from {map_url}: {e}")

        logger.info(f"✅ Extracted {len(players)} player stats from {map_url}")
        return players
