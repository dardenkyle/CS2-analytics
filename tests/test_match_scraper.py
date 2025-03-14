from scraping.match_scraper import MatchScraper

# ✅ Example match URL (replace with real match from HLTV)
test_match_url = "https://www.hltv.org/matches/2379988/legacy-vs-9z-pgl-bucharest-2025-south-america-closed-qualifier"

# Forfeit map URL = https://www.hltv.org/matches/2380592/passion-ua-vs-sashi-yalla-compass-winter-2025
# Bo3 Map URL =  https://www.hltv.org/matches/2380579/wildlotus-vs-9ine-galaxy-battle-2025-starter
# Bo5 map URL = https://www.hltv.org/matches/2379988/legacy-vs-9z-pgl-bucharest-2025-south-america-closed-qualifier
# Bo1 map URL = https://www.hltv.org/matches/2380400/just-swing-vs-gods-reign-esl-challenger-league-season-49-asia-pacific

scraper = MatchScraper()
match_data = scraper.fetch_match_data(test_match_url)
scraper.close()

# ✅ Print results
print("\n🔍 Extracted Match Data:")
print(match_data)