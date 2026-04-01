"""Extracts player stats from a map stats page."""

import datetime as dt
import re

from cs2_analytics.models.player import Player
from cs2_analytics.queues import map_queue
from cs2_analytics.storage.db_instance import db
from cs2_analytics.utils.log_manager import get_logger

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

                    # Parse K(hs) format from column 5: "19(10)" -> kills=19, headshots=10
                    k_hs_match = re.match(r"(\d+)\s*\((\d+)\)", cols[5].text.strip())
                    if k_hs_match:
                        kills = int(k_hs_match.group(1))
                        headshots = int(k_hs_match.group(2))
                    else:
                        kills = 0
                        headshots = 0
                        logger.warning(
                            "Could not parse K(hs) from: %s", cols[5].text.strip()
                        )

                    # Parse A(f) format from column 6: "3(0)" -> assists=3, flash_assists=0
                    a_f_match = re.match(r"(\d+)\s*\((\d+)\)", cols[6].text.strip())
                    if a_f_match:
                        assists = int(a_f_match.group(1))
                        flash_assists = int(a_f_match.group(2))
                    else:
                        assists = 0
                        flash_assists = 0
                        logger.warning(
                            "Could not parse A(f) from: %s", cols[6].text.strip()
                        )

                    # Parse D(q) format from column 7: "16(5)" -> deaths=16
                    d_q_match = re.match(r"(\d+)\s*\((\d+)\)", cols[7].text.strip())
                    if d_q_match:
                        deaths = int(d_q_match.group(1))
                    else:
                        deaths = 0
                        logger.warning(
                            "Could not parse D(q) from: %s", cols[7].text.strip()
                        )

                    # Parse KAST percentage from column 3: "72.7%" -> 0.727
                    try:
                        kast_text = cols[3].text.strip().replace("%", "")
                        kast = round(float(kast_text) / 100, 3)
                    except ValueError:
                        kast = 0.0
                        logger.warning(
                            "Could not parse KAST from: %s", cols[3].text.strip()
                        )

                    # Parse other numeric fields with error handling
                    try:
                        adr = float(cols[8].text.strip())
                    except ValueError:
                        adr = 0.0
                        logger.warning(
                            "Could not parse ADR from: %s", cols[8].text.strip()
                        )

                    # Parse rating from column 10 (skip the Swing column 9 which has percentages)
                    try:
                        rating_text = cols[10].text.strip()
                        # Remove any color indicators or extra formatting
                        rating_clean = (
                            rating_text.replace("+", "")
                            .replace("-", "")
                            .replace("%", "")
                        )
                        rating = float(rating_clean)
                    except (ValueError, IndexError):
                        rating = 0.0
                        logger.warning(
                            "Could not parse Rating from: %s",
                            cols[10].text.strip()
                            if len(cols) > 10
                            else "missing column",
                        )

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
                        deaths=deaths,
                        kast=kast,
                        kd_diff=0,  # OpK-D is ratio format, need different parsing
                        adr=adr,
                        fk_diff=0,  # Not visible in current HLTV format
                        rating=rating,
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
