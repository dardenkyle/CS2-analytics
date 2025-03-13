import time
import random
import re
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from log_manager.logger_config import setup_logger
from config.config import HLTV_URL, MAX_MATCHES, START_DATE, END_DATE

logger = setup_logger(__name__)

class MatchScraper:
    """Scrapes match, map, and player data from HLTV using SeleniumBase."""

    def __init__(self, max_matches=MAX_MATCHES):
        self.max_matches = max_matches
        logger.debug(f"🔧 MatchScraper initialized with max_matches: {self.max_matches}")
        self.driver = Driver(uc=True, headless=True)  # ✅ Use Undetected Chrome Driver
        self.match_data = []
        self.start_date = dt.datetime.strptime(START_DATE, "%Y-%m-%d").date()
        self.end_date = dt.datetime.strptime(END_DATE, "%Y-%m-%d").date()

    def fetch_matches(self):
        """Scrapes matches from HLTV within the date range."""
        offset = 0
        while len(self.match_data) < self.max_matches:
            page_url = f"{HLTV_URL}?offset={offset}"
            logger.info(f"🔄 Scraping: {page_url}")

            new_matches, stop_scraping = self._extract_matches_from_page(page_url)
            self.match_data.extend(new_matches)

            if stop_scraping or len(new_matches) == 0:
                break  # ✅ Stop if no more matches

            offset += 100  # ✅ Move to next page

        logger.info(f"✅ Found {len(self.match_data)} matches from {self.start_date} to {self.end_date}.")
        return self.match_data

    def _extract_matches_from_page(self, url):
        """Extracts match data from a given HLTV results page."""
        self.driver.get(url)
        time.sleep(random.uniform(3, 5))  # ✅ Allow time for page load

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        matches: list[dict] = []
        stop_scraping: bool = False

        # ✅ Find all match date sections
        results_sublist = soup.find_all("div", class_="results-sublist")

        for section in results_sublist:
            date_header = section.find("div", class_="standard-headline")
            
            if date_header:
                raw_date_text = (
                    date_header.text.replace("Results for ", "")
                    .replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
                )

                try:
                    match_date = dt.datetime.strptime(raw_date_text, "%B %d %Y").date()
                except ValueError:
                    logger.warning(f"❌ Could not parse date: {raw_date_text}")
                    continue  # Skip invalid dates

                if match_date > self.end_date:                                                     # Controls how many pages viewed
                    continue  # ✅ Skip future matches
                
                if match_date < self.start_date:
                    logger.info(f"⏩ Match date {match_date} is too old, stopping scraping.")
                    return matches, True  # ✅ Stop if we reached old dates

                # ✅ Extract match data
                match_containers = section.find_all("div", class_="result-con")
                
                for index, match in enumerate(match_containers):  # ✅ Track index
                    if len(matches) >= self.max_matches:  # ✅ Stop when reaching MAX_MATCHES
                        logger.info(f"✅ Reached MAX_MATCHES ({self.max_matches}). Stopping scraping.")
                        return matches, True 
                    
                    match_url = f"https://www.hltv.org{match.find('a', href=True)['href']}"
                    match_id = int(match_url.split("/")[-2])

                    team_names = match.find_all("div", class_="team")
                    team1 = team_names[0].text.strip() if len(team_names) >= 2 else "Unknown"
                    team2 = team_names[1].text.strip() if len(team_names) >= 2 else "Unknown"

                    score_elements = match.find("td", class_="result-score")
                    scores = score_elements.find_all("span") if score_elements else []
                    score1 = int(scores[0].text.strip()) if len(scores) >= 2 else None
                    score2 = int(scores[1].text.strip()) if len(scores) >= 2 else None

                    event = match.find("span", class_="event-name")
                    event_name = event.text.strip() if event else "Unknown Event"
                    
                    type_element = match.find("div", class_="map-text")
                    match_type = type_element.text.strip().upper()
    
                    forfeit = match_type == "DEF"

                    map_stats_links = self.fetch_map_stats_links(match_url)

                    # while forfeit == False:
                    #     if (score1 + score2) < 3:
                    #         data_complete = False                                             # Code to get data_complete. Need to fix the logic in the if statement
                    #     else:                                                                 # Can find games needed from match type. i.e bo3 = 3 games            
                    #         data_complete = True
                    #     break

                    matches.append({
                        "match_id": match_id,
                        "match_url": match_url,
                        "map_stats_links": map_stats_links,
                        "team1": team1,
                        "team2": team2,
                        "score1": score1,
                        "score2": score2,
                        "event": event_name,
                        "match_type": match_type,
                        "forfeit": forfeit,
                        "date": match_date.isoformat(),
                        "data_complete": True
                    })
                    
        return matches, stop_scraping

    def fetch_map_stats_links(self, match_url):
        """Scrapes map stats links from a match details page."""
        logger.info(f"🔄 Fetching map stats links: {match_url}")
        
        self.driver.get(match_url)
        time.sleep(random.uniform(3, 5))  # Allow time for page load

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        map_stats_links = []

        try:
            # ✅ Find all "STATS" buttons that contain map stats links
            stats_links = soup.find_all("a", class_="results-stats")

            for link in stats_links:
                map_stats_url = f"https://www.hltv.org{link['href']}"
                map_stats_links.append(map_stats_url)

            logger.info(f"✅ Found {len(map_stats_links)} map stats links.")

        except Exception as e:
            logger.error(f"❌ Error fetching map stats links: {e}")

        return map_stats_links  # List of URLs

    def fetch_player_stats(self, match_url):
        """Scrapes player statistics from a given match stats page."""

        logger.info(f"🔄 Fetching player stats: {match_url}")
        self.driver.get(match_url)
        time.sleep(random.uniform(3, 5))  # ✅ Allow time for page load

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        player_stats = {}

        try:
            # ✅ Find all team stat tables
            stat_tables = soup.find_all("table", class_="stats-table totalstats")
            if not stat_tables:
                logger.warning(f"⚠️ No player stats found on {match_url}")
                return player_stats

            for table in stat_tables:
                # ✅ Extract team name from <th> inside <thead>
                team_header = table.find("th", class_="st-teamname")
                if not team_header:
                    logger.warning("⚠️ Team name not found in stats table.")
                    continue

                team_name = team_header.text.strip()

                # ✅ Find all player rows in the table
                player_rows = table.find("tbody").find_all("tr")

                for row in player_rows:
                    name_tag = row.find("a")
                    if not name_tag:
                        logger.warning("⚠️ Skipping a row: No player name found.")
                        continue

                    player_name = name_tag.text.strip()
                    player_url = f"https://www.hltv.org{name_tag['href']}"

                    try:
                        player_id = int(name_tag['href'].split("/")[-2])
                    except (ValueError, IndexError):
                        logger.warning(f"⚠️ Could not extract player_id from {name_tag['href']}")
                        player_id = None  # Handle cases where player_id cannot be extracted

                    # ✅ Extract player stats
                    stats = row.find_all("td")
                    stats_count = len(stats)

                    if stats_count < 9:  # Ensure there are enough columns
                        logger.warning(f"⚠️ Skipping {player_name}: Expected 16 stats, found {stats_count}.")
                        continue  # Skip if incomplete data

                    # ✅ Extract values with error handling
                    try:
                        kills_data = stats[1].text.strip().split(" ")  # e.g., "23 (11)"
                        kills = int(kills_data[0])
                        headshots = int(kills_data[1][1:-1]) if len(kills_data) > 1 else 0  # Extracts (xx)

                        assists_data = stats[2].text.strip().split(" ")  # e.g., "3 (0)"
                        assists = int(assists_data[0])
                        flash_assists = int(assists_data[1][1:-1]) if len(assists_data) > 1 else 0

                        def extract_game_id(match_url):
                            """Extracts the game_id from an HLTV match stats URL."""
                            try:
                                game_id = int(match_url.split("/")[-2])  # Extracts the second-to-last part of the URL
                                return game_id
                            except (IndexError, ValueError):
                                return None  # Return None if extraction fails
                        
                        game_id = extract_game_id(match_url)

                        # Find the <div> containing the "Map" label
                        map_div = soup.find("div", class_="small-text")

                        # Initialize extracted_map_name
                        extracted_map_name = None

                        if map_div:
                            # Iterate over the siblings of map_div
                            for sibling in map_div.next_siblings:
                                # Check if the sibling is a NavigableString (i.e., text node)
                                if sibling.string and sibling.string.strip():
                                    extracted_map_name = sibling.string.strip()
                                    break

                        # Output the extracted map name
                        logger.debug(f"Extracted Map Name: {extracted_map_name}")

                        player_stats[player_name] = {
                            "game_id": game_id,
                            "player_id": player_id,
                            "player_name": player_name,
                            "player_url": player_url,
                            "map_name": extracted_map_name,
                            "team_name": team_name,
                            "kills": kills,
                            "headshots": headshots,
                            "assists": assists,
                            "flash_assists": flash_assists,
                            "deaths": int(stats[3].text.strip()),
                            "kast": round(float(stats[4].text.strip('%')) / 100 if "%" in stats[4].text else 0.0, 3),
                            "kd_diff": int(stats[5].text.strip().replace("+", "").replace("−", "-")),  # Normalize signs
                            "adr": float(stats[6].text.strip()),
                            "fk_diff": int(stats[7].text.strip().replace("+", "").replace("−", "-")),
                            "rating": float(stats[8].text.strip()),
                            "data_complete": True
                        }
                        logger.debug(f"✅ Extracted stats for {player_name}")

                    except Exception as e:
                        logger.error(f"❌ Error processing stats for {player_name}: {e}")

        except Exception as e:
            logger.error(f"❌ Error scraping player stats: {e}")

        return player_stats
        

    def fetch_map_stats(self, match_url):                                             # currently not used?
        """Scrapes map data from a given match page."""
        logger.info(f"🔄 Fetching map stats: {match_url}")
        self.driver.get(match_url)
        time.sleep(random.uniform(3, 5))  # ✅ Allow time for page load

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        maps_played = []

        try:
            map_sections = soup.find_all("div", class_="mapholder")
            for i, map_section in enumerate(map_sections, start=1):
                map_name = map_section.find("div", class_="mapname").text.strip()
                team_scores = map_section.find_all("div", class_="results-team-score")

                if len(team_scores) < 2:
                    continue  # ✅ Skip incomplete map data

                team1_score = int(team_scores[0].text.strip())
                team2_score = int(team_scores[1].text.strip())

                winner = "Team1" if team1_score > team2_score else "Team2"

                maps_played.append({
                    "map_id": int(f"{match_url.split('/')[-2]}{i}"),  # Unique map ID
                    "match_id": int(match_url.split("/")[-2]),
                    "map_name": map_name,
                    "map_order": i,
                    "team1_score": team1_score,
                    "team2_score": team2_score,
                    "winner": winner,
                    "date": dt.datetime.now().strftime("%Y-%m-%d")
                })

        except Exception as e:
            logger.error(f"❌ Error scraping map stats: {e}")

        return maps_played

    def close(self):
        """Closes the Selenium driver."""
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")