"""Extracts player stats from a map stats page."""

import re
import datetime as dt
from cs2_analytics.utils.log_manager import get_logger
from cs2_analytics.models.player import Player
from cs2_analytics.queues import map_queue
from cs2_analytics.storage.db_instance import db

logger = get_logger(__name__)


class MapParser:
    """Extracts player stats from a map stats page."""

    def run(self, map_soups: list[tuple]) -> list[Player]:
        """
        Runs parsing logic for a list of soup objects and stores players.

        Args:
            map_soups (list): List of tuples (soup, map_id, map_url)

        Returns:
            List[Player]: All parsed player objects
        """
        all_players = []

        for soup, map_id, map_url in map_soups:
            try:
                players = self.parse_map(soup, map_url)
                db.store_players(players)
                map_queue.mark_parsed(map_id)
                logger.info("✅ Stored %s players for map %s", len(players), map_id)
                all_players.extend(players)
            except Exception as e:
                map_queue.mark_failed(map_id, str(e)[:500])
                logger.error("❌ Failed to parse map %s: %s", map_id, e)

        return all_players

    def __init__(self):
        """Initializes the parser."""

    def parse_map(self, soup, map_url: str, map_id: int) -> list[Player]:
        """Extracts player object from a map stats page."""
        logger.info("Parsing %s for player stats", map_url)
        players = []

        match_box = soup.find("div", class_="match-info-box")

        if match_box:
            # Find the small-text div and get the next sibling that's a string
            small_text_div = match_box.find("div", class_="small-text")
            if small_text_div:
                for elem in small_text_div.next_siblings:
                    if isinstance(elem, str):
                        map_name = elem.strip()
                        if map_name:
                            break
        try:
            tables = soup.find_all("table", class_="stats-table totalstats")
            for table in tables:
                team_header = table.find("th", class_="st-teamname")
                team_name = team_header.text.strip() if team_header else "Unknown"

                player_rows = table.find("tbody").find_all("tr")
                for row in player_rows:
                    cols = row.find_all("td")

                    name_tag = cols[0].find("a")
                    try:
                        player_url = (
                            f"https://www.hltv.org{name_tag['href']}"
                            if name_tag and "href" in name_tag.attrs
                            else None
                        )
                    except Exception as e:
                        player_url = None
                        logger.error("Failed to extract player URL: %s", e)

                    player_id = int(player_url.split("/")[5]) if name_tag else -1

                    player_name = (
                        name_tag.text.strip() if name_tag else cols[0].text.strip()
                    )

                    map_id = int(map_url.split("/")[6])

                    match = re.match(r"(\d+)\s+\((\d+)\)", cols[1].text.strip())
                    if match:
                        kills = int(match.group(1))
                        headshots = int(match.group(2))
                    else:
                        kills = "Error"
                        headshots = "Error"

                    match = re.match(r"(\d+)\s+\((\d+)\)", cols[2].text.strip())
                    if match:
                        assists = int(match.group(1))  # 26
                        flash_assists = int(match.group(2))  # 14
                    else:
                        assists = "Error"
                        flash_assists = "Error"

                    player = Player(
                        map_id=map_id,
                        player_id=player_id,
                        player_name=player_name,
                        player_url=player_url,
                        map_name=map_name or "unknown",
                        team_name=team_name,
                        kills=kills,
                        headshots=headshots,
                        assists=assists,
                        flash_assists=flash_assists,
                        deaths=int(
                            cols[3].text.strip()
                        ),  # may want to adjust if deaths are in different col
                        kast=round(
                            float(cols[4].text.strip().replace("%", "")) / 100, 3
                        ),
                        kd_diff=int(cols[5].text.strip()),
                        adr=float(cols[6].text.strip()),
                        fk_diff=int(cols[7].text.strip()),
                        rating=float(cols[8].text.strip()),
                        last_inserted_at=dt.datetime.now(),
                        last_scraped_at=dt.datetime.now(),
                        last_updated_at=dt.datetime.now(),
                        data_complete=True,
                    )
                    logger.debug("Extracted stats for player: %s", player.player_name)
                    players.append(player)

        except Exception as e:
            logger.error("Failed to extract player stats from %s: %s", map_url, e)

        logger.info("Extracted %s player stats from %s", len(players), map_url)
        return players
