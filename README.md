# **Counter-Strike 2 Pro Match Analytics Tool**

## **Project Overview**

This project is a **Counter-Strike 2 (CS2) analytics tool** focused on collecting professional **match, map, and player data** and turning it into reliable, queryable analytics data. The current development focus is the ingestion pipeline: discovery, match/map processing, relational storage, and clearer lifecycle/state semantics for discovered entities.

---

## **Features**

### **Data Scraping**

- **Match Data:** Scrapes CS2 professional match results (teams, scores, events, etc.).
- **Game Data:** Extracts detailed round-by-round statistics.
- **Player Stats:** Collects individual player performance metrics (kills, deaths, assists, ADR, KAST, opening duels, multi-kills, clutches, round swing, etc.).
- **Ingestion Hardening:** Uses retry/backoff, browser session recovery, and PostgreSQL-backed lifecycle tracking for resilient scraping runs.

### **Deferred / Later-Phase Work**

- **Demo Processing:** Demo download and parsing remain deferred until the active match/map ingestion stages have cleaner lifecycle semantics and thinner controllers.
- **dbt Transformation Layer:** dbt will be added after ingestion/state semantics are stable.
- **Airflow Orchestration:** Airflow comes after dbt and after stage boundaries are cleaner.

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

### **6. Run the API**

```sh
python run_api.py
```

### **7. Run Tests**

```sh
pytest -q
```

Run the map parser hidden-vs-visible regression test directly:

```sh
pytest tests/parsers/test_map_parser_regression.py -v
```

Note: Demo processing is still deferred and is intentionally excluded from standard test runs.

---

## **Quick Start Workflows**

### **Pipeline Mode (Scrape + Processing)**

```sh
python main.py
```

Current focus:

- results discovery
- match and map processing
- relational persistence
- lifecycle/state cleanup for discovered entities

### **API Mode (FastAPI)**

```sh
python run_api.py
```

Then open: `http://127.0.0.1:8000/docs`

---

## **Data Insights & Usage (planned)**

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

## Developer Notes

See `docs/` for:

- architecture overview
- development roadmap

Current architecture direction:

- the main cleanup target is `MatchController` and `MapController`, not `main.py`
- `match_ingestion_state` and `map_ingestion_state` are the active ingestion/discovery lifecycle tables
- the next refactor introduces thinner controllers plus `MatchStageService` and `MapStageService`
- dbt comes after ingestion/state semantics are stable
- Airflow comes after dbt and clean stage boundaries

These documents are used to keep development planning and implementation direction aligned.

## **Contact & Support**

Have questions or want to contribute? Reach out!

- GitHub Issues: [CS2-analytics Issues](https://github.com/dardenkyle/CS2-analytics/issues)
- Email: [dardenkyle@example.com](mailto:dardenkyle@example.com)

**Happy Analyzing!**
