"""Extracts player stats from a map stats page."""

import re
from utils.log_manager import get_logger
from models.player import Player

logger = get_logger(__name__)


class MapParser:
    """Extracts player stats from a map stats page."""

    def __init__(self):
        """Initializes the parser."""

    def parse_map(self, soup, map_url: str, match_id: int) -> list[Player]:
        """Extracts player object from a map stats page."""
        logger.info("Parsing %s for player stats", map_url)
        print(f"Map URL: {map_url}")
        players = []
        print(f"Players: {players}")

        match_box = soup.find("div", class_="match-info-box")

        if match_box:
            # Find the small-text div and get the next sibling that's a string
            small_text_div = match_box.find("div", class_="small-text")
            if small_text_div:
                for elem in small_text_div.next_siblings:
                    if isinstance(elem, str):
                        map_name = elem.strip()
                        if map_name:  # non-empty
                            print(f"✅ Found map name: {map_name}")
                            break
        try:
            tables = soup.find_all("table", class_="stats-table totalstats")
            print(f"📊 Found {len(tables)} stats tables")
            print("✅ 'stats-table' in HTML:", "stats-table" in soup.prettify())
            for table in tables:
                team_header = table.find("th", class_="st-teamname")
                print(team_header)
                team_name = team_header.text.strip() if team_header else "Unknown"
                print(team_name)  # good to here

                player_rows = table.find("tbody").find_all("tr")
                print(len(player_rows))  # Skips header row

                for row in player_rows:
                    cols = row.find_all("td")

                    name_tag = cols[0].find("a")
                    print("name_tag:", name_tag)
                    print("name_tag.attrs:", name_tag.attrs)
                    try:
                        player_url = (
                            f"https://www.hltv.org{name_tag['href']}"
                            if name_tag and "href" in name_tag.attrs
                            else None
                        )
                        print("✅ player_url:", player_url)
                    except Exception as e:
                        print(f"❌ Error extracting player URL: {e}")
                        player_url = None
                    print(player_url)  # working up to here

                    player_id = int(player_url.split("/")[5]) if name_tag else -1
                    print(player_id)

                    player_name = (
                        name_tag.text.strip() if name_tag else cols[0].text.strip()
                    )
                    print(player_name)

                    map_id = int(map_url.split("/")[6])

                    match = re.match(r"(\d+)\s+\((\d+)\)", cols[1].text.strip())
                    if match:
                        kills = int(match.group(1))  # 26
                        headshots = int(match.group(2))  # 14
                        print(kills, headshots)

                    match = re.match(r"(\d+)\s+\((\d+)\)", cols[2].text.strip())
                    if match:
                        assists = int(match.group(1))  # 26
                        flash_assists = int(match.group(2))  # 14
                        print(assists, flash_assists)

                    player = Player(
                        match_id=match_id,
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
                        data_complete=True,
                    )
                    logger.debug("Extracted stats for player: %s", player)
                    print(player)
                    players.append(player)

        except Exception as e:
            logger.error("Failed to extract player stats from %s: %s", map_url, e)

        logger.info("Extracted %s player stats from %s", len(players), map_url)
        return players
