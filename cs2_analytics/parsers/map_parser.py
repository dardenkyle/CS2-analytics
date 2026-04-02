"""Extracts player stats from a map stats page."""

import datetime as dt
import re

from cs2_analytics.models.player import Player
from cs2_analytics.queues import map_queue
from cs2_analytics.storage.player_storage import store_players
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class MapParser:
    """Extracts player stats from a map stats page."""

    def run(self, map_soups: list[tuple[object, int | str, str]]) -> list[Player]:
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
                players = self.parse_map(soup, map_url, map_id)
                store_players(players)
                map_queue.mark_as_parsed(str(map_id))
                logger.info("✅ Stored %s players for map %s", len(players), map_id)
                all_players.extend(players)
            except Exception as e:
                map_queue.mark_as_failed(str(map_id), str(e)[:500])
                logger.error("❌ Failed to parse map %s: %s", map_id, e)

        return all_players

    def __init__(self):
        """Initializes the parser."""

    def parse_map(self, soup, map_url: str, map_id: int | str) -> list[Player]:
        """Extracts player object from a map stats page."""
        logger.info("Parsing %s for player stats", map_url)
        players = []
        map_name = "unknown"
        try:
            map_id_value = int(map_id)
        except (TypeError, ValueError):
            map_id_value = self._extract_numeric_id(map_url)

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
            tables = soup.select("table.stats-table.totalstats")
            if not tables:
                tables = soup.select("table.stats-table")
            for table in tables:
                table_classes = table.get("class", [])
                if "hidden" in table_classes:
                    continue

                team_header = table.find("th", class_="st-teamname")
                team_name = team_header.text.strip() if team_header else "Unknown"

                column_map = self._build_column_map(table)
                opkd_idx = self._pick_col(column_map, ["op.k-d", "opkd", "op.kd"], 1)
                mks_idx = self._pick_col(column_map, ["mks"], 2)
                kast_idx = self._pick_col(column_map, ["kast"], 4)
                clutches_idx = self._pick_col(column_map, ["1vsx", "clutches"], 6)
                kills_idx = self._pick_col(column_map, ["k(hs)", "khs", "kills"], 7)
                assists_idx = self._pick_col(column_map, ["a(f)", "af", "assists"], 9)
                deaths_idx = self._pick_col(
                    column_map, ["d(t)", "dt", "d(q)", "dq", "deaths", "d"], 10
                )
                adr_idx = self._pick_col(column_map, ["adr"], 12)
                round_swing_idx = self._pick_col(
                    column_map, ["swing", "roundswing"], 16
                )
                rating_idx = self._pick_col(
                    column_map,
                    ["rating3.0", "rating30", "rating2.1", "rating2.0", "rating", "rt"],
                    17,
                )

                tbody = table.find("tbody")
                if not tbody:
                    logger.warning("Skipping table without tbody in %s", map_url)
                    continue

                player_rows = tbody.find_all("tr")
                for row in player_rows:
                    cols = row.find_all("td")
                    if not cols:
                        continue

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

                    player_id = (
                        self._extract_numeric_id(player_url) if player_url else -1
                    )

                    player_name = (
                        name_tag.text.strip() if name_tag else cols[0].text.strip()
                    )

                    # Parse K(hs) format from column 5: "19(10)" -> kills=19, headshots=10
                    kills_text = self._row_metric_text(
                        cols,
                        kills_idx,
                        ["st-kills"],
                    )
                    kills, headshots = self._parse_pair(kills_text)

                    # Parse A(f) format from column 6: "3(0)" -> assists=3, flash_assists=0
                    assists_text = self._row_metric_text(
                        cols,
                        assists_idx,
                        ["st-assists"],
                    )
                    assists, flash_assists = self._parse_pair(assists_text)

                    # Parse D(t) format from table: "16(5)" -> deaths=16, traded_deaths=5
                    deaths_text = self._row_metric_text(
                        cols,
                        deaths_idx,
                        ["st-deaths"],
                    )
                    deaths, traded_deaths = self._parse_pair(deaths_text)

                    opening_kills, opening_deaths = self._parse_colon_pair(
                        self._row_metric_text(cols, opkd_idx, ["st-opkd"])
                    )
                    multi_kills = self._parse_int_value(
                        self._row_metric_text(cols, mks_idx, ["st-mks"])
                    )
                    clutches_won = self._parse_int_value(
                        self._row_metric_text(cols, clutches_idx, ["st-clutches"])
                    )
                    round_swing = self._parse_percent_value(
                        self._row_metric_text(
                            cols,
                            round_swing_idx,
                            ["st-roundSwing"],
                            prefer_hidden=False,
                        )
                    )

                    # Parse KAST percentage from column 3: "72.7%" -> 0.727
                    try:
                        kast_text = self._row_metric_text(
                            cols,
                            kast_idx,
                            ["st-kast"],
                            prefer_hidden=False,
                        ).replace("%", "")
                        kast = round(float(kast_text) / 100, 3)
                    except ValueError:
                        kast = 0.0
                        logger.warning(
                            "Could not parse KAST from: %s",
                            self._row_metric_text(cols, kast_idx, ["st-kast"]),
                        )

                    # Parse other numeric fields with error handling
                    try:
                        adr = float(
                            self._row_metric_text(
                                cols,
                                adr_idx,
                                ["st-adr"],
                                prefer_hidden=False,
                            )
                        )
                    except ValueError:
                        adr = 0.0
                        logger.warning(
                            "Could not parse ADR from: %s",
                            self._row_metric_text(cols, adr_idx, ["st-adr"]),
                        )

                    # Parse rating from column 10 (skip the Swing column 9 which has percentages)
                    try:
                        rating_text = self._row_metric_text(
                            cols,
                            rating_idx,
                            ["st-rating"],
                            prefer_hidden=False,
                        )
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
                            self._row_metric_text(cols, rating_idx, ["st-rating"]),
                        )

                    kd_diff = kills - deaths
                    fk_diff = opening_kills - opening_deaths

                    player = Player(
                        map_id=map_id_value,
                        player_id=player_id,
                        player_name=player_name,
                        player_url=player_url or "",
                        map_name=map_name or "unknown",
                        team_name=team_name,
                        kills=kills,
                        headshots=headshots,
                        assists=assists,
                        flash_assists=flash_assists,
                        deaths=deaths,
                        traded_deaths=traded_deaths,
                        opening_kills=opening_kills,
                        opening_deaths=opening_deaths,
                        multi_kills=multi_kills,
                        clutches_won=clutches_won,
                        kast=kast,
                        kd_diff=kd_diff,
                        adr=adr,
                        fk_diff=fk_diff,
                        round_swing=round_swing,
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

    def _normalize_header(self, value: str) -> str:
        return re.sub(r"[^a-z0-9.]", "", value.lower())

    def _build_column_map(self, table) -> dict[str, int]:
        """Builds a normalized header->index map from table headers."""
        mapping = {}
        header_cells = table.select("thead th")
        for idx, th in enumerate(header_cells):
            text = th.get_text(" ", strip=True)
            if not text:
                continue
            normalized = self._normalize_header(text)
            if normalized not in mapping:
                mapping[normalized] = idx
        return mapping

    def _pick_col(self, mapping: dict[str, int], keys: list[str], default: int) -> int:
        """Returns the first matching column index from candidate normalized keys."""
        for key in keys:
            normalized = self._normalize_header(key)
            if normalized in mapping:
                return mapping[normalized]
        return default

    def _safe_col_text(self, cols, idx: int) -> str:
        if idx < len(cols):
            return str(cols[idx].get_text(strip=True))
        return ""

    def _row_metric_text(
        self,
        cols,
        fallback_idx: int,
        metric_classes: list[str],
        prefer_hidden: bool = False,
    ) -> str:
        """Gets metric text using row cell classes with index fallback."""
        visible_match: str | None = None
        hidden_match: str | None = None

        for td in cols:
            classes = td.get("class", [])
            if not classes:
                continue

            if not any(metric_class in classes for metric_class in metric_classes):
                continue

            text = td.get_text(" ", strip=True)
            if not text:
                continue

            is_hidden = "hidden" in classes or "eco-adjusted-data" in classes
            if is_hidden:
                if hidden_match is None:
                    hidden_match = text
            elif visible_match is None:
                visible_match = text

        if prefer_hidden:
            if hidden_match is not None:
                return hidden_match
            if visible_match is not None:
                return visible_match
        else:
            if visible_match is not None:
                return visible_match
            if hidden_match is not None:
                return hidden_match

        return self._safe_col_text(cols, fallback_idx)

    def _parse_pair(self, text: str) -> tuple[int, int]:
        """Parses values like '19(10)' into tuple (19, 10)."""
        match = re.search(r"(\d+)\s*\((\d+)\)", text)
        if match:
            return int(match.group(1)), int(match.group(2))

        single = re.search(r"(\d+)", text)
        if single:
            return int(single.group(1)), 0
        return 0, 0

    def _extract_numeric_id(self, url: str) -> int:
        match = re.search(r"/(\d+)/", url)
        if match:
            return int(match.group(1))
        return -1

    def _parse_colon_pair(self, text: str) -> tuple[int, int]:
        """Parses values like '5 : 0' into tuple (5, 0)."""
        match = re.search(r"(\d+)\s*:\s*(\d+)", text)
        if match:
            return int(match.group(1)), int(match.group(2))
        return 0, 0

    def _parse_int_value(self, text: str) -> int:
        match = re.search(r"-?\d+", text)
        if match:
            return int(match.group(0))
        return 0

    def _parse_percent_value(self, text: str) -> float:
        """Parses values like '+14.68%' into 0.1468."""
        match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
        if match:
            return round(float(match.group(1)) / 100, 4)
        return 0.0
