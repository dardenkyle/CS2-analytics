import re
import time
import random
import datetime as dt
from seleniumbase import Driver
from bs4 import BeautifulSoup
from utils.log_manager import get_logger

logger = get_logger(__name__)

class MatchScraper:
    """Scrapes match details, demo links, and map stats links from HLTV match pages."""

    def __init__(self):
        """Initializes the scraper with SeleniumBase driver."""
        self.driver = Driver(uc=True, headless=True)  # ✅ Undetected Chrome for stealth

    def fetch_match_data(self, match_url):
        """Extracts match details, demo links, and map stats links from a single match page."""
        logger.info(f"🔄 Fetching match data from: {match_url}")

        self.driver.get(match_url)
        time.sleep(random.uniform(3, 5))  # ✅ Allow time for page load

        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        # ✅ Extract match details
        match_data = self._extract_match_info(soup, match_url)
        
        # ✅ Extract demo links
        match_data["demo_links"] = self._extract_demo_links(soup)                                           # Where demo links are appended to the match_data dict

        # ✅ Extract map stats links (for player stats)
        match_data["map_stats_links"] = self._extract_map_stats_links(soup)

        logger.info(f"✅ Extracted match data: {match_data['team1']} vs {match_data['team2']}")
        return match_data

    def _extract_match_info(self, soup, match_url):
        """Extracts match details like teams, scores, event, and type."""
        try:
            team_names = soup.find_all("div", class_="teamName")
            team1 = team_names[0].text.strip() if len(team_names) >= 2 else "Unknown"
            team2 = team_names[1].text.strip() if len(team_names) >= 2 else "Unknown"

            # ✅ Extract scores
            team1_gradient = soup.find("div", class_="team1-gradient")
            score1 = team1_gradient.a.find_next_sibling("div").text.strip()

            team2_gradient = soup.find("div", class_="team2-gradient")
            score2 = team2_gradient.a.find_next_sibling("div").text.strip()

            # ✅ Extract event name                                                                        # Refactor start
            event_tag = soup.find("div", class_="event text-ellipsis")
            event = event_tag.text.strip() if event_tag else "Unknown Event"

            # ✅ Extract match type (BO1, BO3, etc.)
            match_type_tag = soup.find("div", class_="padding preformatted-text")                                             
            match_type = match_type_tag.text.strip().upper() if match_type_tag else "UNKNOWN"
            best_of_temp = re.search(r"^(.*?)(?=\n|$)", match_type)
            best_type = best_of_temp.group(1).strip() if best_of_temp else "Unknown"
            print(best_type)
                                                                                                            # Refactor this code
            def determine_match_type(text: str) -> str:
                """Determines match type based on presence of '3' or '5' in the text."""
                if "3" in text:
                    return "bo3"
                elif "5" in text:
                    return "bo5"
                else:
                    return "bo1"

            best_ty: str = determine_match_type(best_type)                                                      # Refactor end

            # ✅ Check if match was forfeited
            map_name_check = soup.find("div", class_="mapname").text.lower()
            forfeit = map_name_check == "default"

            # ✅ Extract match date
            match_date_tag = soup.find("div", class_="date")
            match_date = dt.datetime.fromtimestamp(int(match_date_tag["data-unix"]) / 1000).strftime("%Y-%m-%d") if match_date_tag else None

            return {
                "match_id": int(match_url.split("/")[-2]),
                "match_url": match_url,
                "team1": team1,
                "team2": team2,
                "score1": score1,
                "score2": score2,
                "event": event,
                "match_type": best_ty,
                "forfeit": forfeit,
                "date": match_date,
            }
        except Exception as e:
            logger.error(f"❌ Error extracting match info: {e}")
            return {}                                                  

    def _extract_demo_links(self, soup) -> list:
        """Extracts demo download links from the match page."""

        try:
            demo_link_tag = soup.find("a", class_="stream-box")
            # ✅ Extract the "data-demo-link" attribute
            demo_var = demo_link_tag["data-demo-link"] if demo_link_tag else None                                                          
            demo_link = (f"https://www.hltv.org{demo_var}")                                                             # refactor this code -- it works for now

            logger.info(f"📥 Successfully found demo link.")
        except Exception as e:
            logger.error(f"❌ Error extracting demo link: {e}")

        return demo_link

    def _extract_map_stats_links(self, soup) -> list:
        """Extracts map stats links for player performance analysis."""
        map_stats_links: list = []
        try:
            stats_buttons = soup.find_all("a", class_="results-stats")
            for btn in stats_buttons:
                map_stats_links.append(f"https://www.hltv.org{btn['href']}")

            logger.info(f"📊 Found {len(map_stats_links)} map stats links.")
        except Exception as e:
            logger.error(f"❌ Error extracting map stats links: {e}")

        return map_stats_links

    def close(self) -> None:
        """Closes the Selenium driver."""
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")
