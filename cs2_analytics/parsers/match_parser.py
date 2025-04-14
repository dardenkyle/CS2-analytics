"""Parses match metadata from HLTV match pages."""

import re
import datetime as dt
from cs2_analytics.utils.queue_helpers import chunk_and_queue
from cs2_analytics.utils.log_manager import get_logger
from cs2_analytics.models.match import Match
from cs2_analytics.queues import map_queue, demo_queue, match_queue
from cs2_analytics.storage.db_instance import db
from cs2_analytics.scrapers.match_scraper import MatchScraper


logger = get_logger(__name__)


class MatchParser:
    """Parses match metadata from HLTV match pages."""

    def parse_match(self, soup, match_url: str) -> Match:
        """Parses match metadata and returns a Match object. Queues map and demo links."""
        try:
            match_id = match_url.split("/")[-2]

            team1, team2 = self._extract_teams(soup)
            logger.debug("Team1: %s Team2: %s", team1, team2)

            # Extract scores
            team1_gradient = soup.find("div", class_="team1-gradient")
            score1 = int(team1_gradient.a.find_next_sibling("div").text.strip())

            team2_gradient = soup.find("div", class_="team2-gradient")
            score2 = int(team2_gradient.a.find_next_sibling("div").text.strip())

            winner = team1 if score1 > score2 else team2
            logger.debug("Winner: %s", winner)

            # Extract event name
            event_tag = soup.find("div", class_="event text-ellipsis")
            event = event_tag.text.strip() if event_tag else "Unknown Event"

            # Extract match type (BO1, BO3, etc.)
            match_type_tag = soup.find("div", class_="padding preformatted-text")
            match_type = (
                match_type_tag.text.strip().upper() if match_type_tag else "UNKNOWN"
            )
            best_of_temp = re.search(r"^(.*?)(?=\n|$)", match_type)
            best_type = best_of_temp.group(1).strip() if best_of_temp else "Unknown"

            def determine_match_type(text: str) -> str:
                """Determines match type based on presence of '3' or '5' in the text."""
                if "3" in text:
                    return "bo3"
                elif "5" in text:
                    return "bo5"
                else:
                    return "bo1"

            best_ty: str = determine_match_type(best_type)

            # Check if match was forfeited
            map_name_check = soup.find("div", class_="mapname").text.lower()
            forfeit = map_name_check == "default"

            # Extract match date
            match_date_tag = soup.find("div", class_="date")
            match_date = (
                dt.datetime.fromtimestamp(
                    int(match_date_tag["data-unix"]) / 1000
                ).strftime("%Y-%m-%d")
                if match_date_tag and match_date_tag.has_attr("data-unix")
                else None
            )

            demo_links = self._extract_demo_links(soup)
            map_links = self._extract_map_stats_links(soup)

            for demo_id, demo_url in demo_links:
                demo_queue.queue(demo_id, demo_url, source="match_parser")
            for map_id, map_url in map_links:
                map_queue.queue(map_id, map_url, source="match_parser")

            match_obj = Match(
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
                match_type=best_ty,
                forfeit=forfeit,
                date=match_date,
                last_inserted_at=dt.datetime.now(),
                last_scraped_at=dt.datetime.now(),
                last_updated_at=dt.datetime.now(),
                data_complete=True,
            )

            return match_obj, map_links, demo_links

        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.error("Error extracting match info: %s", e)
            return None

    def _extract_teams(self, soup) -> tuple[str, str]:
        """Extracts team names from the match page."""
        team_names = soup.find_all("div", class_="teamName")
        try:
            team1, team2 = [t.text.strip() for t in team_names[0:2]]
        except ValueError as e:
            logger.error("Error extracting team names: %s", e)
            return None, None
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
            logger.error("Error extracting demo link: %s", e)
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
            logger.error("Error extracting map stats links: %s", e)
        return map_links

    def _extract_id(self, url: str) -> str:
        """Extracts the first numeric ID from a URL."""
        match = re.search(r"(\d+)", url)
        return match.group(1) if match else url
