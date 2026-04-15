"""Parses match metadata from HLTV match pages."""

import datetime as dt
import re

from cs2_analytics.exceptions import MatchParseError
from cs2_analytics.models.match import Match
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


class MatchParser:
    """Parses match metadata from HLTV match pages."""

    def parse_match(
        self, soup, match_url: str
    ) -> tuple[Match, list[tuple[str, str]], list[tuple[str, str]]]:
        """Parses match metadata and returns match data with extracted follow-up links."""
        try:
            match_id = self._extract_match_id(match_url)
            metadata = self._extract_match_metadata(soup)
            map_links, demo_links = self._extract_follow_up_links(soup)
            match_obj = self._build_match(
                match_id=match_id,
                match_url=match_url,
                map_links=map_links,
                demo_links=demo_links,
                **metadata,
            )

            return match_obj, map_links, demo_links

        except MatchParseError:
            raise
        except (AttributeError, ValueError, TypeError, KeyError) as e:
            raise MatchParseError(f"Failed to parse match page: {match_url}") from e

    def _extract_match_id(self, match_url: str) -> int:
        """Extracts the match identifier from the match URL."""
        match = re.search(r"/matches/(\d+)", match_url)
        if not match:
            raise MatchParseError("Failed to extract match id from match URL.")
        return int(match.group(1))

    def _extract_follow_up_links(
        self, soup
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """Extracts map and demo follow-up links from the match page."""
        map_links = self._extract_map_stats_links(soup)
        demo_links = self._extract_demo_links(soup)
        return map_links, demo_links

    def _extract_match_metadata(self, soup) -> dict[str, str | int | bool]:
        """Extracts the core match fields needed to build a Match model."""
        team1, team2 = self._extract_teams(soup)
        logger.debug("Team1: %s Team2: %s", team1, team2)
        score1, score2 = self._extract_scores(soup)
        winner = self._determine_winner(team1, team2, score1, score2)
        event = self._extract_event_name(soup)
        match_type = self._extract_match_type(soup)
        forfeit = self._extract_forfeit_status(soup)
        match_date = self._extract_match_date(soup)

        return {
            "team1": team1,
            "team2": team2,
            "score1": score1,
            "score2": score2,
            "winner": winner,
            "event": event,
            "match_type": match_type,
            "forfeit": forfeit,
            "match_date": match_date,
        }

    def _determine_winner(self, team1: str, team2: str, score1: int, score2: int) -> str:
        """Determines the winning team name from the parsed scores."""
        winner = team1 if score1 > score2 else team2
        logger.debug("Winner: %s", winner)
        return winner

    def _build_match(
        self,
        *,
        match_id: int,
        match_url: str,
        map_links: list[tuple[str, str]],
        demo_links: list[tuple[str, str]],
        team1: str,
        team2: str,
        score1: int,
        score2: int,
        winner: str,
        event: str,
        match_type: str,
        forfeit: bool,
        match_date: str,
    ) -> Match:
        """Builds a Match model from already-extracted values."""
        now = dt.datetime.now()
        return Match(
            match_id=match_id,
            match_url=match_url,
            map_links=map_links,
            demo_links=demo_links,
            team1=team1,
            team2=team2,
            score1=score1,
            score2=score2,
            winner=winner,
            event=event,
            match_type=match_type,
            forfeit=forfeit,
            date=match_date,
            last_inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )

    def _extract_teams(self, soup) -> tuple[str, str]:
        """Extracts team names from the match page."""
        team_names = soup.find_all("div", class_="teamName")
        try:
            team1, team2 = [t.get_text(strip=True) for t in team_names[0:2]]
        except ValueError as e:
            raise MatchParseError("Missing team names on match page.") from e
        if not team1 or not team2:
            raise MatchParseError("Missing team names on match page.")
        return team1, team2

    def _extract_demo_links(self, soup) -> list[tuple[str, str]]:
        """Extracts demo download links using class='stream-box' with 'data-demo-link' attributes."""
        demo_links = []
        try:
            demo_link_tag = soup.find("a", class_="stream-box")
            if demo_link_tag and demo_link_tag.has_attr("data-demo-link"):
                url = f"https://www.hltv.org{demo_link_tag['data-demo-link']}"
                demo_id = self._extract_id(url)
                demo_links.append((demo_id, url))
            logger.info("Successfully found %s demo link(s).", len(demo_links))
        except (AttributeError, IndexError) as e:
            raise MatchParseError("Invalid demo link markup on match page.") from e
        return demo_links

    def _extract_map_stats_links(self, soup) -> list[tuple[str, str]]:
        """Extracts map stats links from buttons with class='results-stats'."""
        map_links = []
        try:
            stats_buttons = soup.find_all("a", class_="results-stats")
            for btn in stats_buttons:
                if btn.has_attr("href"):
                    url = f"https://www.hltv.org{btn['href']}"
                    map_id = self._extract_id(url)
                    map_links.append((map_id, url))
            logger.info("Found %s map stats links.", len(map_links))
        except (AttributeError, IndexError) as e:
            raise MatchParseError("Invalid map link markup on match page.") from e
        return map_links

    def _extract_id(self, url: str) -> str:
        """Extracts the first numeric ID from a URL."""
        match = re.search(r"(\d+)", url)
        return match.group(1) if match else url

    def _extract_scores(self, soup) -> tuple[int, int]:
        """Extracts both team scores from the match page."""
        try:
            team1_gradient = soup.find("div", class_="team1-gradient")
            score1 = int(team1_gradient.a.find_next_sibling("div").text.strip())

            team2_gradient = soup.find("div", class_="team2-gradient")
            score2 = int(team2_gradient.a.find_next_sibling("div").text.strip())
        except (AttributeError, TypeError, ValueError) as e:
            raise MatchParseError("Failed to extract team scores from match page.") from e
        return score1, score2

    def _extract_event_name(self, soup) -> str:
        """Extracts the event name for the match."""
        event_tag = soup.find("div", class_="event text-ellipsis")
        if event_tag:
            event_name = event_tag.text.strip()
            if event_name:
                return event_name
        raise MatchParseError("Failed to extract event name from match page.")

    def _extract_match_type(self, soup) -> str:
        """Extracts a normalized best-of value such as bo1, bo3, or bo5."""
        match_type_tag = soup.find("div", class_="padding preformatted-text")
        if not match_type_tag:
            raise MatchParseError("Failed to extract match type from match page.")

        match_type_text = match_type_tag.text.strip().upper()
        if not match_type_text:
            raise MatchParseError("Failed to extract match type from match page.")

        best_of_match = re.search(r"^(.*?)(?=\n|$)", match_type_text)
        if not best_of_match:
            raise MatchParseError("Failed to extract match type from match page.")

        best_of_text = best_of_match.group(1).strip()
        return self._normalize_best_of_type(best_of_text)

    def _normalize_best_of_type(self, text: str) -> str:
        """Maps the scraped best-of text into the normalized match type."""
        if "3" in text:
            return "bo3"
        if "5" in text:
            return "bo5"
        if "1" in text:
            return "bo1"
        raise MatchParseError("Failed to extract match type from match page.")

    def _extract_forfeit_status(self, soup) -> bool:
        """Extracts whether the match was forfeited/defaulted."""
        map_name_tag = soup.find("div", class_="mapname")
        if not map_name_tag:
            raise MatchParseError("Failed to extract forfeit status from match page.")
        map_name = map_name_tag.get_text(strip=True)
        if not map_name:
            raise MatchParseError("Failed to extract forfeit status from match page.")
        return map_name.lower() == "default"

    def _extract_match_date(self, soup) -> str:
        """Extracts the match date in YYYY-MM-DD format."""
        match_date_tag = soup.find("div", class_="date")
        if not match_date_tag or not match_date_tag.has_attr("data-unix"):
            raise MatchParseError("Failed to extract match date from match page.")

        try:
            return dt.datetime.fromtimestamp(
                int(match_date_tag["data-unix"]) / 1000
            ).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError, OverflowError) as e:
            raise MatchParseError("Failed to extract match date from match page.") from e
