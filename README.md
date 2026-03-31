# **Counter-Strike 2 Pro Match Analytics Tool**

## **Project Overview**

This project is a **Counter-Strike 2 (CS2) analytics tool** designed to scrape professional **match, game, and player data**, download demos, parse demo files, and analyze player performance. The goal is to help players **gain insights into maps, matchups, and player statistics** based on the analysis of real professional match data.

---

## **Features**

### **Data Scraping**

- **Match Data:** Scrapes CS2 professional match results (teams, scores, events, etc.).
- **Game Data:** Extracts detailed round-by-round statistics.
- **Player Stats:** Collects individual player performance metrics (kills, deaths, assists, ADR, etc.).

### **Demo File Download & Parsing (Under Development)**

- Automatically **downloads demos** of matches for deeper analysis.
- Parses **demo files** to extract movement, grenade usage, and combat engagements.

### **Player Analytics & Insights (Not Yet Added)**

- **Combines scraped match/map/player stats with parsed demo data** for in-depth analysis.
- Helps players understand **map control, team strategies, and player efficiency.**
- Generates **matchup insights** to improve player knowledge of competitive playstyles.

---

## **Tech Stack**

- **Python 3.11+**
- **Seleniumbase & BeautifulSoup** (for web scraping)
- **PostgreSQL** (for structured data storage)
- **Pandas & NumPy** (for analytics and data processing)
- **Web scraping + demo parsing tools**

---

## **Project Structure**

```
CS2-Analytics/
├── main.py
├── run_api.py
├── README.md
├── pyproject.toml
├── api/
|   ├── main.py
|   ├── routes/
|   ├── schemas/
|   └── services/
├── backend/
|   └── main.py
├── cs2_analytics/
|   ├── config/
|   ├── controllers/
|   ├── models/
|   ├── parsers/
|   ├── pipeline/
|   ├── queues/
|   ├── scrapers/
|   ├── services/
|   ├── storage/
|   └── utils/
├── logs/
|   └── app.log
├── tests/
|   ├── parsers/
|   ├── scrapers/
|   └── storage/
├── demos/
├── parsed_data/
└── frontend/
```

---

## **Installation & Setup**

### **1. Clone the Repository**

```sh
git clone https://github.com/dardenkyle/CS2-analytics.git
cd CS2-Analytics
```

### **2. Create a Virtual Environment**

```sh
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **3. Install Dependencies**

```sh
pip install -e .
# Optional (recommended for local development)
pip install -e ".[dev]"
```

### **4. Set Up Database**

Ensure you have **PostgreSQL installed** and update `cs2_analytics/config/config.py` with your database credentials.

```python
DB_NAME = "cs2_db"
DB_USER = "your_user"
DB_PASS = "your_password"
DB_HOST = "localhost"
DB_PORT = "5432"
```

Run:

```sh
# Run this once to set up your database schema
python -m cs2_analytics.storage.initialize_db
```

### **5. Run the Scraper**

```sh
python main.py
```

### **6. Generate Player Analytics**

```sh
python -m cs2_analytics.services.player_analytics
```

### **7. Run Tests**

```sh
pytest -q
```

Note: Demo scraping/parsing is still in progress and is intentionally excluded from standard test runs.

---

## **Quick Start Workflows**

### **Pipeline Mode (Scrape + Processing)**

```sh
python main.py
```

### **API Mode (FastAPI)**

```sh
python run_api.py
```

Then open: `http://127.0.0.1:8000/docs`

---

## **Data Insights & Usage**

### **Match & Player Stats**

- View **per-match player performance**.
- Compare **teams' win rates on specific maps**.
- Identify **key players in matchups**.

### **Demo Analysis**

- **Heatmaps** of player movements.
- **Grenade usage patterns** and efficiency.
- **Kill zone maps** showing key engagements.

### **Future Improvements**

- AI-based **predictive modeling** for player performance.
- **Automated video highlight generation** from demos.
- **Cloud database integration** for long-term data storage.

---

## **License**

This project is licensed under the **MIT License** – feel free to contribute and modify!

---

## **Contributing**

### **Want to help improve this project?**

1. **Fork the repository** on GitHub.
2. **Create a feature branch** (`git checkout -b new-feature`).
3. **Commit changes** (`git commit -m "Added new feature"`).
4. **Push to GitHub** (`git push origin new-feature`).
5. **Submit a Pull Request** – we review & merge!

---

## **Contact & Support**

Have questions or want to contribute? Reach out!

- GitHub Issues: [CS2-analytics Issues](https://github.com/dardenkyle/CS2-analytics/issues)
- Email: [dardenkyle@example.com](mailto:dardenkyle@example.com)

**Happy Analyzing!**
