import re
import random
import time
from bs4 import BeautifulSoup
from seleniumbase import Driver

driver = Driver(uc=True, headless=True)                                                     # Headless = False for debugging

def extract_match_details(match_url):
    """Extracts detailed player stats from the match page."""
    driver.get(match_url)
    time.sleep(random.uniform(3, 5))
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ✅ Find the Map Stats page
    map_stats_link = soup.find_all("a", class_="results-stats")
    if not map_stats_link:
        print(f"⚠️ No map stats link found for {match_url}")
        return {}                                                               # ❌ This is why you're getting "No player stats found"

    player_stats = {}

    # for link in map_stats_link:  # ✅ Iterate through all map stats links
    #     map_url = f"https://www.hltv.org{link['href']}"                                   #Testing lower code
    #     print(f"✅ Found map stats link: {map_url}")  # ✅ Debugging output

    total_links = len(map_stats_link)  # Get total number of map stats links

    for index, link in enumerate(map_stats_link, start=1):  # ✅ Iterate with index
        map_url = f"https://www.hltv.org{link['href']}"
        print(f"✅ Found map stats link {index}/{total_links}")  # ✅ Debugging output

    # map_url = f"https://www.hltv.org{map_stats_link['href']}"
    driver.get(map_url)
    time.sleep(random.uniform(3, 5))
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ✅ Scrape player stats from table
    player_stats = {}
    stat_table = soup.find("table", class_="stats-table")
    if not stat_table:
        print(f"⚠️ No stats table found on {map_url}")
        return {}

    def extract_kills_and_headshots(text):
        """Extracts kills and headshots from a text like '18 (9)'"""
        match = re.match(r"(\d+)\s*\((\d+)\)", text)  # Regex to match "18 (9)"
        if match:
            kills = int(match.group(1))      # First number = Kills
            headshots = int(match.group(2))  # Second number = Headshots
        else:
            kills = int(re.search(r"\d+", text).group(0)) if re.search(r"\d+", text) else 0
            headshots = 0  # Default to 0 if no headshots recorded
        return kills, headshots

    def extract_assists_and_flash_assists(text):
        """Extracts kills and headshots from a text like '18 (9)'"""
        match = re.match(r"(\d+)\s*\((\d+)\)", text)  # Regex to match "18 (9)"
        if match:
            assists = int(match.group(1))      # First number = Kills
            flash_assists = int(match.group(2))  # Second number = Headshots
        else:
            assists = int(re.search(r"\d+", text).group(0)) if re.search(r"\d+", text) else 0
            flash_assists = 0  # Default to 0 if no headshots recorded
        return assists, flash_assists

    def clean_percentage(value):
        """Removes '%' and converts to float."""
        return float(value.replace("%", "")) if "%" in value else float(value)

    for row in stat_table.find_all("tr")[1:]:  # Skip headers
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        player_name = cols[0].text.strip()
        kills, headshots = extract_kills_and_headshots(cols[1].text.strip())  # Extract both values
        assists, flash_assists = extract_assists_and_flash_assists(cols[2].text.strip())

        player_stats[player_name] = {
            "kills": kills,
            "headshots": headshots,
            "assists": assists,
            "flash_assists": flash_assists,
            "deaths": int(cols[3].text.strip()),
            "kast": clean_percentage(cols[4].text.strip()),
            "kd_diff": cols[5].text.strip(),
            "fk_diff": cols[6].text.strip(),
            "adr": float(cols[7].text.strip()),
            "rating": float(cols[8].text.strip()),
        }

    if not player_stats:
        print(f"⚠️ Scraped player stats but found none on {map_url}")

    return player_stats
