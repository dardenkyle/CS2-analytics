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
- Deployment baseline: containerized runtime, environment-driven configuration,
  migrations, CI, and smoke tests come before dbt.
- dbt transformation layer: dbt follows the deployment baseline and stays
  downstream of ingestion.
- Airflow orchestration: Airflow comes after dbt and clean stage boundaries.

## Tech Stack

- Python 3.14+
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

### 4. Configure Environment Variables

Copy `.env.example` to `.env` for local development and adjust the values for
your PostgreSQL instance.

Required runtime variables:

| Variable | Purpose | Local example |
| --- | --- | --- |
| `ENVIRONMENT` | Runtime environment name. Use `production` for deployed runtime validation. | `development` |
| `DEBUG_MODE` | Enables debug logging and API reload behavior. Must be `false` in production. | `true` |
| `API_HOST` | Host address used by `python run_api.py`. | `127.0.0.1` |
| `API_PORT` | Port used by `python run_api.py`. | `8000` |
| `API_CORS_ORIGINS` | Comma-separated browser origins allowed by the API. Wildcard CORS is rejected in production. | `http://localhost:8501` |
| `DB_NAME` | PostgreSQL database name. | `cs2_db` |
| `DB_USER` | PostgreSQL user. | `postgres` |
| `DB_PASS` | PostgreSQL password. | `change_me` |
| `DB_HOST` | PostgreSQL host. | `localhost` |
| `DB_PORT` | PostgreSQL port. | `5432` |

Production mode fails fast when required runtime variables are missing, when
`DEBUG_MODE=true`, or when `API_CORS_ORIGINS` includes `*`.

### 5. Set Up Database

Ensure PostgreSQL is installed and configure database credentials through your
local environment or `.env`.

Run:

```sh
python manage_db.py --init
```

Running `python manage_db.py` with no flags also uses the safe init path.

For first-time local setup when the configured PostgreSQL database does not
exist yet:

```sh
python manage_db.py --create-database
```

To explicitly wipe application tables:

```sh
python manage_db.py --wipe
```

The wipe command asks for `y` confirmation before dropping tables.

### 6. Run the Pipeline

```sh
python main.py
```

### 7. Run the API

```sh
python run_api.py
```

Then open the host and port configured by `API_HOST` and `API_PORT`, such as
`http://127.0.0.1:8000/docs`.

### 8. Run Tests

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

- Current API surface includes a player-oriented read path for top players by
  average rating.
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
- Phase 3.5 dbt readiness is complete for the active `matches`, `maps`, and
  `players` grains.
- The next major architecture phase is the Phase 3.75 deployment baseline.
- dbt scaffolding and staging models follow after the deployment baseline.
- Demo pipeline implementation remains deferred.
- Airflow comes after dbt and clean transformation boundaries.

## License

This project is licensed under the MIT License.

## Contact & Support

- GitHub Issues: [CS2-analytics Issues](https://github.com/dardenkyle/CS2-analytics/issues)
- Email: [dardenkyle@example.com](mailto:dardenkyle@example.com)
