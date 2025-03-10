import random
import time
import datetime as dt
from bs4 import BeautifulSoup
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logger_config import setup_logger

logger = setup_logger(__name__)

target_date = dt.date(2025,3,4)  # Adjust start date is 2025,1,29

# ✅ Initialize WebDriver (Headless Mode)
driver = Driver(uc=True, headless=False)                                                        # Headless = False for debugging.

# ✅ Function to Extract Match Data from a Page
def extract_matches_from_page(url) -> list:
    driver.get(url)
    time.sleep(random.uniform(3, 5))  # Dynamic wait time
    soup = BeautifulSoup(driver.page_source, "html.parser")

    matches = []
    stop_scraping = False

    # ✅ Locate all date sections
    results_sublist = soup.find_all("div", class_="results-sublist")

    for section in results_sublist:
        date_header = section.find("div", class_="standard-headline")
        if date_header:
            raw_date_text = (
                date_header.text.replace("Results for ", "")
                .replace("st", "")
                .replace("nd", "")
                .replace("rd", "")
                .replace("th", "")
            )
            
            try:
                match_date_obj = dt.datetime.strptime(raw_date_text, "%B %d %Y").date()
            except ValueError:
                logger.error(f"❌ Could not parse date: {raw_date_text}")
                continue  # Skip invalid dates

            if match_date_obj >= target_date:
                # ✅ Extract match data under this date
                match_containers = section.find_all("div", class_="result-con")
                for match in match_containers:
                    match_url = f"https://www.hltv.org{match.find('a', href=True)['href']}"
                    team_names = match.find_all("div", class_="team")
                    team1 = team_names[0].text.strip() if len(team_names) >= 2 else "Unknown"
                    team2 = team_names[1].text.strip() if len(team_names) >= 2 else "Unknown"

                    score_elements = match.find("td", class_="result-score")
                    scores = score_elements.find_all("span") if score_elements else []
                    score1 = scores[0].text.strip() if len(scores) >= 2 else "?"
                    score2 = scores[1].text.strip() if len(scores) >= 2 else "?"

                    event = match.find("span", class_="event-name")
                    event_name = event.text.strip() if event else "Unknown Event"

                    matches.append(
                        {
                            "match_url": match_url,
                            "date": match_date_obj.isoformat(),
                            "team1": team1,
                            "team2": team2,
                            "score1": score1,
                            "score2": score2,
                            "event": event_name,
                        }
                    )
            elif  match_date_obj < target_date:
                    logger.info(f"⏩ Date {match_date_obj} is too old, stopping pagination.")
                    return matches, True  # ✅ Stop only if we found target date
    return matches, stop_scraping