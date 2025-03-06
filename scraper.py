import random
import time
import csv
import json
from bs4 import BeautifulSoup
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime as dt

# ✅ Initialize Headless Browser
driver = Driver(uc=True, headless=False)

HLTV_URL = "https://www.hltv.org/results"
target_date = dt.date(2025,1,29) # Start of season 2.
print(target_date)
print(type(target_date))

# ✅ Navigate to HLTV.org & Accept Necessary Cookies
driver.get(url=HLTV_URL)
time.sleep(random.uniform(3, 5))  # Wait for Cloudflare validation

try:
    cookie_button = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonDecline"))
    )
    cookie_button.click()
    print("✅ Successfully clicked 'Use necessary cookies only'")
except Exception:
    print("⚠️ No cookie popup detected. Continuing...")

time.sleep(random.uniform(2, 4))  # Small delay after clicking cookies

# ✅ Function to Extract Match Data from a Page
def extract_matches_from_page(url):
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
                print(f"❌ Could not parse date: {raw_date_text}")
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
                    print(f"⏩ Date {match_date_obj} is too old, stopping pagination.")
                    return matches, True  # ✅ Stop only if we found target date
    return matches, stop_scraping

# ✅ Iterate Through Pagination Until We Reach Older Dates
match_data = []
offset = 0
while True:
    page_url = f"{HLTV_URL}?offset={offset}"
    print(f"🔄 Checking page: {page_url}", end='\r')

    extracted_matches, stop_scraping = extract_matches_from_page(page_url)
    match_data.extend(extracted_matches)

    if stop_scraping or len(extracted_matches) == 0:
        break  # Stop if no more matches or we found an older date

    offset += 100  # Move to the next page

print(f"✅ Found {len(match_data)} matches from {target_date}, including {target_date}.")

# ✅ Save Data to CSV
csv_file = "hltv_matches.csv"
with open(csv_file, "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(
        [
            "Match URL",
            "Team 1",
            "Team 2",
            "Score 1",
            "Score 2",
            "Event",
            "Date",
        ]
    )

    for match in match_data:
        writer.writerow(
            [
                match["match_url"],
                match["team1"],
                match["team2"],
                match["score1"],
                match["score2"],
                match["event"],
                match["date"],
            ]
        )

print(f"✅ Data successfully saved to {csv_file}")

# ✅ Save Data to JSON
if match_data:
    with open("hltv_matches.json", "w", encoding="utf-8") as json_file:
        json.dump(match_data, json_file, indent=4)
    print("✅ Data successfully saved to hltv_matches.json")
else:
    print("⚠️ No match data collected! JSON will be empty.")

# ✅ Close Selenium Driver
driver.quit()