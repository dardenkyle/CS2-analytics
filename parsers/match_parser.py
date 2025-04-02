"""Parses match metadata from HLTV match pages."""

import re
import datetime as dt
from utils.log_manager import get_logger
from models.match import Match


logger = get_logger(__name__)


class MatchParser:
    """Parses match metadata from HLTV match pages."""

    def parse_match(self, soup, match_url: str) -> Match:
        """Parses match metadata and returns a Match object."""
        try:
            match_id = match_url.split("/")[-2]

            team_names = soup.find_all("div", class_="teamName")
            team1 = team_names[0].text.strip() if len(team_names) >= 2 else "Unknown"
            team2 = team_names[1].text.strip() if len(team_names) >= 2 else "Unknown"

            # Extract scores
            team1_gradient = soup.find("div", class_="team1-gradient")
            score1 = int(team1_gradient.a.find_next_sibling("div").text.strip())

            team2_gradient = soup.find("div", class_="team2-gradient")
            score2 = int(team2_gradient.a.find_next_sibling("div").text.strip())

            winner = team2
            if score1 > score2:
                winner = team1

            # Extract event name
            event_tag = soup.find("div", class_="event text-ellipsis")
            event = event_tag.text.strip() if event_tag else "Unknown Event"

            #
            # Refactor start
            #
            # Extract match type (BO1, BO3, etc.)
            match_type_tag = soup.find("div", class_="padding preformatted-text")
            match_type = (
                match_type_tag.text.strip().upper() if match_type_tag else "UNKNOWN"
            )
            best_of_temp = re.search(r"^(.*?)(?=\n|$)", match_type)
            best_type = best_of_temp.group(1).strip() if best_of_temp else "Unknown"

            # Refactor this code
            def determine_match_type(text: str) -> str:
                """Determines match type based on presence of '3' or '5' in the text."""
                if "3" in text:
                    return "bo3"
                elif "5" in text:
                    return "bo5"
                else:
                    return "bo1"

            best_ty: str = determine_match_type(best_type)
            #
            #
            # Refactor end
            #

            # Check if match was forfeited
            map_name_check = soup.find("div", class_="mapname").text.lower()
            forfeit = map_name_check == "default"

            # Extract match date
            match_date_tag = soup.find("div", class_="date")
            match_date = (
                dt.datetime.fromtimestamp(
                    int(match_date_tag["data-unix"]) / 1000
                ).strftime("%Y-%m-%d")
                if match_date_tag
                else None
            )

            demo_links = self._extract_demo_links(soup)
            map_links = self._extract_map_stats_links(soup)

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
                match_type=best_ty,
                forfeit=forfeit,
                date=match_date,
                inserted_at=dt.datetime.now(),
                last_scraped=dt.datetime.now(),
                last_updated=dt.datetime.now(),  # need to fix
                data_complete=True,
            )

        except Exception as e:
            logger.error("Error extracting match info: %s", e)
            return {}

    def _extract_demo_links(self, soup) -> list:
        """Extracts demo download links from the match page."""

        try:
            demo_link_tag = soup.find("a", class_="stream-box")
            # ✅ Extract the "data-demo-link" attribute
            demo_var = demo_link_tag["data-demo-link"] if demo_link_tag else None
            demo_link = f"https://www.hltv.org{demo_var}"  # refactor this code -- it works for now

            logger.info("Successfully found demo link.")
        except Exception as e:
            logger.error("Error extracting demo link: %s", e)

        return demo_link

    def _extract_map_stats_links(self, soup) -> list:
        """Extracts map stats links for player performance analysis."""
        map_stats_links: list = []
        try:
            stats_buttons = soup.find_all("a", class_="results-stats")
            for btn in stats_buttons:
                map_stats_links.append(f"https://www.hltv.org{btn['href']}")

            logger.info("Found %s map stats links.", len(map_stats_links))
        except Exception as e:
            logger.error("Error extracting map stats links: %s", e)

        return map_stats_links
