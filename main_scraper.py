import db_connection
import match_scraper
import player_scraper
import demo_scraper
import data_storage
import datetime as dt

HLTV_URL = "https://www.hltv.org/results"
target_date = dt.date(2025,3,6)                                         # Start of season 2 is 2025,1,29.  Controls the date of the matches we scrape.

def main():
    print("Starting script at:", dt.datetime.now())
    print("🚀 Ensuring database is ready...")
    db_connection.ensure_tables()  # ✅ This runs before scraping

    print("🚀 Starting HLTV Scraper...")
    
    # # ✅ Iterate Through Pagination Until We Reach Older Dates
    # match_data = []
    # offset = 0

    # while True:
    #     page_url = f"{HLTV_URL}?offset={offset}"
    #     print(f"🔄 Checking page: {page_url}", end='\r')

    #     extracted_matches, stop_scraping = match_scraper.extract_matches_from_page(page_url)
    #     match_data.extend(extracted_matches)

    #     if stop_scraping or len(extracted_matches) == 0:
    #         break  # Stop if no more matches or we found an older date

    #     offset += 100  # Move to the next page

    # print(f"✅ Found {len(match_data)} matches from {target_date}, including {target_date}.")



    MAX_MATCHES = 1  # ✅ Set a limit for debugging

    match_data = []
    offset = 0

    while len(match_data) < MAX_MATCHES:  # ✅ Stop scraping once we reach the limit
        page_url = f"{HLTV_URL}?offset={offset}"
        print(f"🔄 Checking page: {page_url}", end='\r')

        extracted_matches, stop_scraping = match_scraper.extract_matches_from_page(page_url)
        
        for match in extracted_matches:
            if len(match_data) >= MAX_MATCHES:  # ✅ Stop once we hit the limit
                break
            match_data.append(match)

        if stop_scraping or len(match_data) >= MAX_MATCHES:
            break  # ✅ Stop if no more matches or we reached the limit

        offset += 100  # Move to the next page

    print(f"✅ Found {len(match_data)} matches for debugging.")

    # Store match data in a list before inserting
    match_list = []
    player_stats_list = []

    for match in match_data:
        match_id = match["match_url"].split("/")[4]
        match_list.append((match_id, match["match_url"], match["team1"], match["team2"], match["score1"], match["score2"], match["event"], match["date"]))



        # Fetch player stats
        player_stats = player_scraper.extract_match_details(match["match_url"])
        for player_name, stats in player_stats.items():  # ✅ Iterate correctly over dictionary
            player_stats_list.append((
                match_id,                                                                              ## Fix this
                player_name,  # ✅ Use key as player's name
                stats["kills"],
                stats["headshots"],  # ✅ Updated for new stat
                stats["assists"],
                stats["flash_assists"],  # ✅ New column
                stats["deaths"],
                stats["kast"],
                stats["kd_diff"],
                stats["adr"],
                stats["fk_diff"],
                stats["rating"]
            ))
    # Insert match data in **one query**
    data_storage.batch_insert_matches(match_list)

    # Insert player stats in **one query**
    data_storage.batch_insert_player_stats(player_stats_list)

    print("✅ Scraping completed!")

if __name__ == "__main__":
    main()