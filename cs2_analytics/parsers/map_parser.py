"""Extracts player stats from a map stats page."""

import datetime as dt
import re

from cs2_analytics.exceptions import MapParseError
from cs2_analytics.models.player import Player
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class MapParser:
    """Extracts player stats from a map stats page."""

    def parse_map(self, soup, map_url: str, map_id: int) -> list[Player]:
        """Extracts player object from a map stats page."""
        logger.info("Parsing %s for player stats", map_url)
        try:
            map_id_value = self._resolve_map_id(map_id)
            map_name = self._extract_map_name(soup)
            players = self._extract_players_from_tables(
                soup=soup,
                map_url=map_url,
                map_id_value=map_id_value,
                map_name=map_name,
            )

        except MapParseError:
            raise
        except Exception as e:
            raise MapParseError(f"Failed to parse map stats page: {map_url}") from e

        logger.info("Extracted %s player stats from %s", len(players), map_url)
        return players

    def _resolve_map_id(self, map_id: int) -> int:
        """Resolves the numeric map identifier from the explicit id or URL."""
        return map_id

    def _iter_visible_stat_tables(self, soup):
        """Yields visible player stat tables from the map page."""
        tables = soup.select("table.stats-table.totalstats")
        if not tables:
            tables = soup.select("table.stats-table")
        if not tables:
            raise MapParseError("No player stats tables found on map page.")

        for table in tables:
            table_classes = table.get("class", [])
            if "hidden" in table_classes:
                continue
            yield table

    def _extract_team_name(self, table) -> str:
        """Extracts the team name heading for a player stats table."""
        team_header = table.find("th", class_="st-teamname")
        return team_header.text.strip() if team_header else "Unknown"

    def _extract_players_from_tables(
        self, *, soup, map_url: str, map_id_value: int, map_name: str
    ) -> list[Player]:
        """Extracts parsed player rows from each visible stats table."""
        players: list[Player] = []

        for table in self._iter_visible_stat_tables(soup):
            team_name = self._extract_team_name(table)
            column_indexes = self._build_column_indexes(table)
            tbody = table.find("tbody")
            if not tbody:
                logger.warning("Skipping table without tbody in %s", map_url)
                continue

            for row in tbody.find_all("tr"):
                player = self._parse_player_row(
                    row=row,
                    map_id_value=map_id_value,
                    map_name=map_name,
                    team_name=team_name,
                    column_indexes=column_indexes,
                )
                if player is None:
                    continue
                logger.debug("Extracted stats for player: %s", player.player_name)
                players.append(player)

        return players

    def _build_column_indexes(self, table) -> dict[str, int]:
        """Builds the column indexes used to parse a stats table row."""
        column_map = self._build_column_map(table)
        return {
            "opkd": self._pick_column_index(column_map, ["op.k-d", "opkd", "op.kd"], 1),
            "mks": self._pick_column_index(column_map, ["mks"], 2),
            "kast": self._pick_column_index(column_map, ["kast"], 4),
            "clutches": self._pick_column_index(
                column_map, ["1vsx", "clutches"], 6
            ),
            "kills": self._pick_column_index(
                column_map, ["k(hs)", "khs", "kills"], 7
            ),
            "assists": self._pick_column_index(
                column_map, ["a(f)", "af", "assists"], 9
            ),
            "deaths": self._pick_column_index(
                column_map, ["d(t)", "dt", "d(q)", "dq", "deaths", "d"], 10
            ),
            "adr": self._pick_column_index(column_map, ["adr"], 12),
            "round_swing": self._pick_column_index(
                column_map, ["swing", "roundswing"], 16
            ),
            "rating": self._pick_column_index(
                column_map,
                ["rating3.0", "rating30", "rating2.1", "rating2.0", "rating", "rt"],
                17,
            ),
        }

    def _parse_player_row(
        self,
        *,
        row,
        map_id_value: int,
        map_name: str,
        team_name: str,
        column_indexes: dict[str, int],
    ) -> Player | None:
        """Parses a single player row into a Player model."""
        cols = row.find_all("td")
        if not cols:
            return None

        player_name, player_url, player_id = self._extract_player_identity(cols)
        stats = self._extract_player_stats(cols, column_indexes)
        return self._build_player(
            map_id_value=map_id_value,
            player_id=player_id,
            player_name=player_name,
            player_url=player_url,
            map_name=map_name,
            team_name=team_name,
            stats=stats,
        )

    def _extract_player_identity(self, cols) -> tuple[str, str, int]:
        """Extracts player display identity from the first row cell."""
        name_tag = cols[0].find("a")
        player_url = self._extract_player_url(name_tag)
        player_id = self._extract_numeric_id(player_url) if player_url else -1
        player_name = self._extract_player_name(cols, name_tag)
        return player_name, player_url or "", player_id

    def _extract_player_url(self, name_tag) -> str | None:
        """Extracts the absolute player URL when one is present."""
        try:
            if name_tag and "href" in name_tag.attrs:
                return f"https://www.hltv.org{name_tag['href']}"
        except Exception:
            return None
        return None

    def _extract_player_stats(
        self, cols, column_indexes: dict[str, int]
    ) -> dict[str, int | float]:
        """Extracts parsed combat and utility stats from a player row."""
        kills, headshots = self._extract_kills(cols, column_indexes["kills"])
        assists, flash_assists = self._extract_assists(cols, column_indexes["assists"])
        deaths, traded_deaths = self._extract_deaths(cols, column_indexes["deaths"])
        opening_kills, opening_deaths = self._parse_colon_pair(
            self._extract_metric_text(cols, column_indexes["opkd"], ["st-opkd"])
        )
        multi_kills = self._parse_int_value(
            self._extract_metric_text(cols, column_indexes["mks"], ["st-mks"])
        )
        clutches_won = self._parse_int_value(
            self._extract_metric_text(
                cols, column_indexes["clutches"], ["st-clutches"]
            )
        )
        round_swing = self._parse_percent_value(
            self._extract_metric_text(
                cols,
                column_indexes["round_swing"],
                ["st-roundSwing"],
                prefer_hidden=False,
            )
        )
        kast = self._extract_kast(cols, column_indexes["kast"])
        adr = self._extract_adr(cols, column_indexes["adr"])
        rating = self._extract_rating(cols, column_indexes["rating"])

        return {
            "kills": kills,
            "headshots": headshots,
            "assists": assists,
            "flash_assists": flash_assists,
            "deaths": deaths,
            "traded_deaths": traded_deaths,
            "opening_kills": opening_kills,
            "opening_deaths": opening_deaths,
            "multi_kills": multi_kills,
            "clutches_won": clutches_won,
            "round_swing": round_swing,
            "kast": kast,
            "adr": adr,
            "rating": rating,
        }

    def _extract_kills(self, cols, kills_idx: int) -> tuple[int, int]:
        """Extracts kills and headshots from the player row."""
        kills_text = self._require_metric_text(
            self._extract_metric_text(cols, kills_idx, ["st-kills"]),
            "No player kills logged.",
        )
        return self._parse_pair(kills_text)

    def _extract_assists(self, cols, assists_idx: int) -> tuple[int, int]:
        """Extracts assists and flash assists from the player row."""
        assists_text = self._extract_metric_text(cols, assists_idx, ["st-assists"])
        return self._parse_pair(assists_text)

    def _extract_deaths(self, cols, deaths_idx: int) -> tuple[int, int]:
        """Extracts deaths and traded deaths from the player row."""
        deaths_text = self._require_metric_text(
            self._extract_metric_text(cols, deaths_idx, ["st-deaths"]),
            "No player deaths logged.",
        )
        return self._parse_pair(deaths_text)

    def _extract_kast(self, cols, kast_idx: int) -> float:
        """Extracts KAST as a decimal ratio."""
        try:
            kast_text = self._extract_metric_text(
                cols,
                kast_idx,
                ["st-kast"],
                prefer_hidden=False,
            ).replace("%", "")
            return round(float(kast_text) / 100, 3)
        except ValueError:
            logger.warning(
                "Could not parse KAST from: %s",
                self._extract_metric_text(cols, kast_idx, ["st-kast"]),
            )
            return 0.0

    def _extract_adr(self, cols, adr_idx: int) -> float:
        """Extracts ADR as a float value."""
        try:
            return float(
                self._extract_metric_text(
                    cols,
                    adr_idx,
                    ["st-adr"],
                    prefer_hidden=False,
                )
            )
        except ValueError:
            logger.warning(
                "Could not parse ADR from: %s",
                self._extract_metric_text(cols, adr_idx, ["st-adr"]),
            )
            return 0.0

    def _extract_rating(self, cols, rating_idx: int) -> float:
        """Extracts rating as a float value."""
        try:
            rating_text = self._extract_metric_text(
                cols,
                rating_idx,
                ["st-rating"],
                prefer_hidden=False,
            )
            rating_clean = rating_text.replace("+", "").replace("-", "").replace("%", "")
            return float(rating_clean)
        except (ValueError, IndexError):
            logger.warning(
                "Could not parse Rating from: %s",
                self._extract_metric_text(cols, rating_idx, ["st-rating"]),
            )
            return 0.0

    def _build_player(
        self,
        *,
        map_id_value: int,
        player_id: int,
        player_name: str,
        player_url: str,
        map_name: str,
        team_name: str,
        stats: dict[str, int | float],
    ) -> Player:
        """Builds a Player model from a parsed row."""
        now = dt.datetime.now()
        kills = int(stats["kills"])
        deaths = int(stats["deaths"])
        opening_kills = int(stats["opening_kills"])
        opening_deaths = int(stats["opening_deaths"])

        return Player(
            map_id=map_id_value,
            player_id=player_id,
            player_name=player_name,
            player_url=player_url,
            map_name=map_name,
            team_name=team_name,
            kills=kills,
            headshots=int(stats["headshots"]),
            assists=int(stats["assists"]),
            flash_assists=int(stats["flash_assists"]),
            deaths=deaths,
            traded_deaths=int(stats["traded_deaths"]),
            opening_kills=opening_kills,
            opening_deaths=opening_deaths,
            multi_kills=int(stats["multi_kills"]),
            clutches_won=int(stats["clutches_won"]),
            kast=float(stats["kast"]),
            kd_diff=kills - deaths,
            adr=float(stats["adr"]),
            fk_diff=opening_kills - opening_deaths,
            round_swing=float(stats["round_swing"]),
            rating=float(stats["rating"]),
            last_inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )

    def _normalize_header(self, value: str) -> str:
        return re.sub(r"[^a-z0-9.]", "", value.lower())

    def _extract_map_name(self, soup) -> str:
        """Extracts the map name from the match info box."""
        match_box = soup.find("div", class_="match-info-box")
        if not match_box:
            raise MapParseError("Failed to extract map name from map stats page.")

        small_text_div = match_box.find("div", class_="small-text")
        if not small_text_div:
            raise MapParseError("Failed to extract map name from map stats page.")

        for elem in small_text_div.next_siblings:
            if isinstance(elem, str):
                map_name = elem.strip()
                if map_name:
                    return map_name

        raise MapParseError("Failed to extract map name from map stats page.")

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

    def _extract_player_name(self, cols, name_tag) -> str:
        """Extracts a non-empty player name from the first stats cell."""
        if name_tag:
            player_name = name_tag.get_text(strip=True)
            if player_name:
                return player_name

        if cols:
            player_name = cols[0].get_text(strip=True)
            if player_name:
                return player_name

        raise MapParseError("Failed to extract player name from map stats page.")

    def _pick_column_index(
        self, mapping: dict[str, int], keys: list[str], default: int
    ) -> int:
        """Returns the first matching column index from candidate normalized keys."""
        for key in keys:
            normalized = self._normalize_header(key)
            if normalized in mapping:
                return mapping[normalized]
        return default

    def _column_text_or_empty(self, cols, idx: int) -> str:
        if idx < len(cols):
            return str(cols[idx].get_text(strip=True))
        return ""

    def _extract_metric_text(
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

        return self._column_text_or_empty(cols, fallback_idx)

    def _parse_pair(self, text: str) -> tuple[int, int]:
        """Parses values like '19(10)' into tuple (19, 10)."""
        match = re.search(r"(\d+)\s*\((\d+)\)", text)
        if match:
            return int(match.group(1)), int(match.group(2))

        single = re.search(r"(\d+)", text)
        if single:
            return int(single.group(1)), 0
        return 0, 0

    def _require_metric_text(self, text: str, message: str) -> str:
        """Raises a parsing error when a required metric cell is missing."""
        if text:
            return text
        raise MapParseError(message)

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
