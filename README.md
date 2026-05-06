# Counter-Strike 2 Pro Match Analytics Tool

## Project Overview

This project is a Counter-Strike 2 analytics tool focused on collecting professional match, map, and player data and turning it into reliable, queryable analytics data.

The current ingestion architecture uses PostgreSQL-backed ingestion-state tables, thin controllers for batch orchestration, and stage services for per-item match/map/demo workflow boundaries.

## Features

### Data Ingestion

- Results discovery refreshes match ingestion-state rows.
- Match processing collects match metadata and discovers downstream map/demo links.
- Map processing collects player performance metrics such as kills, deaths, assists, ADR, KAST, opening duels, multi-kills, clutches, and round swing.
- Ingestion hardening uses retry/backoff, browser session recovery, and lifecycle tracking for resilient scraping runs.

### Deferred / Later-Phase Work

- Demo processing: demo download and parsing remain deferred, though `DemoStageService` preserves the stage boundary.
- dbt transformation layer: dbt comes after ingestion/state semantics and active stage boundaries are stable.
- Airflow orchestration: Airflow comes after dbt and clean stage boundaries.

## Tech Stack

- Python 3.11+
- SeleniumBase and BeautifulSoup for web scraping
- PostgreSQL for structured data storage
- Pandas and NumPy for analytics/data processing
- FastAPI for API work

## Project Structure

```text
CS2-Analytics/
|-- main.py
|-- run_api.py
|-- README.md
|-- pyproject.toml
|-- api/
|   |-- main.py
|   |-- routes/
|   |-- schemas/
|   `-- services/
|-- cs2_analytics/
|   |-- config/
|   |-- controllers/
|   |-- ingestion_state/
|   |-- models/
|   |-- parsers/
|   |-- pipeline/
|   |-- scrapers/
|   |-- stage_services/
|   |-- services/
|   |-- storage/
|   `-- utils/
|-- docs/
|-- logs/
|-- tests/
|-- demos/
|-- parsed_data/
`-- frontend/
```

## Installation & Setup

### 1. Clone the Repository

```sh
git clone https://github.com/dardenkyle/CS2-analytics.git
cd CS2-Analytics
```

### 2. Create a Virtual Environment

```sh
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```sh
pip install -e .
pip install -e ".[dev]"
```

### 4. Set Up Database

Ensure PostgreSQL is installed and configure database credentials through your local environment or `cs2_analytics/config/config.py`.

Run:

```sh
python -m cs2_analytics.storage.initialize_db
```

### 5. Run the Pipeline

```sh
python main.py
```

### 6. Run the API

```sh
python run_api.py
```

Then open: `http://127.0.0.1:8000/docs`

### 7. Run Tests

```sh
python -m pytest
```

Note: Demo processing is still deferred and intentionally remains outside the active ingestion pipeline.

## Architecture Notes

Current stage boundaries:

- Controllers coordinate batches, retry policy, scraper reset/rotation, and summaries.
- Stage services own per-item fetch, parse, persist, and lifecycle outcome work.
- Scrapers fetch remote content only.
- Parsers convert fetched content into structured outputs only.
- Storage modules centralize relational writes.
- Ingestion-state tables track lifecycle for discovered matches, maps, and demos.

Current active flow:

```text
results discovery
-> match_ingestion_state refresh
-> MatchController batch
-> MatchStageService per-item workflow
-> map/demo ingestion-state refresh
-> MapController batch
-> MapStageService per-item workflow
-> relational storage
```

## Data Insights & Usage (planned)

- View per-match player performance.
- Compare teams' win rates on specific maps.
- Identify key players in matchups.
- Add transformed analytics models through dbt.
- Expand API read paths over trusted transformed tables.

## Developer Notes

See `docs/` for architecture and roadmap details.

Current architecture direction:

- Phase 2 ingestion-state migration is complete.
- Phase 3 controller thinning is complete.
- The next major architecture phase is dbt, not more controller refactoring.
- Demo pipeline implementation remains deferred.
- Airflow comes after dbt and clean transformation boundaries.

## License

This project is licensed under the MIT License.

## Contact & Support

- GitHub Issues: [CS2-analytics Issues](https://github.com/dardenkyle/CS2-analytics/issues)
- Email: [dardenkyle@example.com](mailto:dardenkyle@example.com)
