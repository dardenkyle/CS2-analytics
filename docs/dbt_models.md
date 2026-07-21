# dbt Models

This document describes the planned dbt model structure for the CS2 Analytics project.

dbt is the Phase 4 transformation layer. The project skeleton is initialized
under `dbt/` (#109): an environment-driven Postgres profile reusing the
application's `DB_*` variables, and source declarations for the Alembic-owned
`matches`, `maps`, and `players` tables. Models are still planned work.

dbt is not part of the ingestion pipeline; it consumes ingestion outputs
downstream. Setup and run commands are in the README.

Note:
Planned raw snapshot tables (for example `raw_matches` and `raw_maps`) are expected to be introduced around dbt rollout time, not before.

Completed prerequisite order:

1. review lifecycle semantics for the current match/map discovery tables
2. update the current state tables and their audit fields
3. thin `MatchController` and `MapController` by introducing stage services
4. stabilize the active `matches`, `maps`, and `players` grains for dbt
   readiness

Next dependency:

5. add dbt scaffolding and staging models over the active parsed-source tables

---

## Purpose

dbt will be used to transform raw and structured PostgreSQL tables into clean, analytics-ready models.

Its role in this project is to:

- separate transformation logic from application logic
- standardize and clean parsed data
- create reusable intermediate models
- produce trustworthy fact and dimension tables
- support testing and documentation
- prepare the project for analytics use cases and API consumption

---

## What dbt Is Responsible For

dbt is responsible for:

- selecting from raw and structured source tables
- renaming and standardizing fields
- casting data types
- filtering invalid or incomplete rows where appropriate
- joining related entities
- producing analytics-ready fact and dimension tables
- running data quality tests
- generating lineage and documentation

---

## What dbt Is Not Responsible For

dbt is not responsible for:

- scraping
- parsing HTML
- downloading demos
- transactional application writes
- ingestion-state orchestration
- API request handling

Those concerns belong elsewhere in the system.

dbt should consume stable ingestion outputs, not compensate for ingestion-state or lifecycle problems.

---

## Planned Model Layers

The dbt project should be organized into three main layers:

- staging
- intermediate
- marts

Snapshots (SCD2 change tracking) sit alongside the model layers under
`snapshots/`; see the Snapshot Layer section.

This keeps transformations readable, modular, and maintainable.

---

# 1. Staging Layer

Status: the parsed-source staging models `stg_matches`, `stg_maps`, and
`stg_players` are implemented (#110) as thin views under
`dbt/models/staging/`, with grains and columns documented in
`dbt/models/staging/_staging__models.yml`. The `stg_raw_*` snapshot models
below remain planning-only; the pipeline does not persist raw HTML snapshots,
so those are not built.

The staging layer standardizes raw inputs and structured source tables.

These models should do light cleanup only.

Typical staging responsibilities:

- rename columns consistently
- cast data types
- trim or normalize text values
- expose one clean representation of each source table
- avoid business-heavy logic

## Planned staging models

### stg_raw_matches

Purpose:

- standardize fields from raw match snapshots
- expose cleaned raw match metadata
- support traceability back to raw source records

Possible responsibilities:

- select raw match records
- expose match_url, scraped_at, raw_metadata
- standardize timestamp formats
- expose raw_html only if truly needed downstream

---

### stg_raw_maps

Purpose:

- standardize fields from raw map snapshots
- provide a clean source for downstream debugging or raw lineage

Possible responsibilities:

- expose map_url, scraped_at, raw_metadata
- standardize timestamps
- preserve linkage to parsed map records where relevant

---

### stg_matches

Purpose:

- clean and standardize the parsed matches table

Possible responsibilities:

- cast match date fields
- normalize team names if needed
- standardize booleans such as forfeit and data_complete
- expose only trusted columns

Example fields:

- match_id
- match_url
- team1
- team2
- score1
- score2
- winner, or `match_winner` as a staging alias
- event
- match_type
- match_date
- forfeit
- data_complete
- last_inserted_at, or `inserted_at` after the planned source schema
  normalization
- last_scraped_at
- last_updated_at

---

### stg_maps

Purpose:

- clean and standardize the parsed maps table

Possible responsibilities:

- cast numeric score fields
- normalize map names
- standardize `map_winner`
- preserve foreign key relationship to match_id

Example fields:

- map_id
- match_id
- map_url
- map_order
- map_name
- team1_score
- team2_score
- map_winner
- data_complete
- inserted_at
- last_scraped_at
- last_updated_at

---

### stg_players

Purpose:

- clean and standardize per-map player statistics

Possible responsibilities:

- cast kills, deaths, assists, rating, kast, adr
- normalize player and team name text
- preserve composite grain of one row per player per map

Example fields:

- map_id
- player_id
- player_name
- player_url
- team_name
- kills
- deaths
- assists
- headshots
- kast
- adr
- rating
- kd_diff
- fk_diff
- data_complete
- last_inserted_at, or `inserted_at` after the planned source schema
  normalization
- last_scraped_at
- last_updated_at

---

### stg_player_info

Purpose:

- standardize stable player identity data

Possible responsibilities:

- normalize player names
- standardize country fields
- preserve stable player identifiers

---

### stg_teams

Purpose:

- standardize stable team data

Possible responsibilities:

- normalize team names
- expose canonical team identifiers

---

# 2. Intermediate Layer

Status: `int_match_player_stats` is implemented (#111) under
`dbt/models/intermediate/` as a reusable-join view over the staging models
(grain: one row per player per map), documented in
`dbt/models/intermediate/_intermediate__models.yml`. The other `int_*` models
below remain planning-only until a mart needs them.

The intermediate layer handles reusable joins and logic that should not be repeated in marts.

These models are not always exposed directly to end users or the API.

Typical intermediate responsibilities:

- join staging models together
- calculate reusable derived fields
- isolate transformation steps
- reduce duplication across marts

## Planned intermediate models

### int_match_player_stats

Purpose:

- join player performance rows to maps and matches
- provide a reusable enriched player performance table

Possible responsibilities:

- join stg_players to stg_maps using map_id
- join stg_maps to stg_matches using match_id
- attach match-level metadata to player rows

Possible output fields:

- match_id
- map_id
- player_id
- player_name
- team_name
- match_date
- event
- map_name
- kills
- deaths
- assists
- adr
- kast
- rating

---

### int_team_match_results

Purpose:

- create one reusable model of team-level match results

Possible responsibilities:

- reshape match records into team-centric rows
- derive win/loss flags
- support future team performance analytics

Possible output grain:

- one row per team per match

Possible fields:

- match_id
- team_id or team_name
- opponent_team_name
- event
- match_date
- won_match
- score_for
- score_against

---

### int_player_match_aggregates

Purpose:

- aggregate per-map player rows into match-level player summaries

Possible responsibilities:

- group per-map rows by match_id and player_id
- compute total kills, deaths, assists across a match
- compute average or weighted metrics where appropriate

Possible fields:

- match_id
- player_id
- total_kills
- total_deaths
- total_assists
- avg_rating
- avg_adr
- avg_kast

---

### int_event_matches

Purpose:

- isolate match/event relationships for future event analytics

Possible responsibilities:

- standardize event names
- support future event dimension creation
- make event-based filtering easier

---

# 3. Mart Layer

Status: an initial mart set is implemented (#112) under `dbt/models/marts/` as
tables, documented in `dbt/models/marts/_marts__models.yml`:
`fact_player_map_stats` (player-per-map, built on `int_match_player_stats`),
`fact_matches` (per match), `dim_players` (per player), and `dim_maps` (per map
name). The other fact/dim models below remain planning-only.

The mart layer contains business-ready models intended for analytics, reporting, and API use.

These should be the cleanest and most trusted representations of the data.

Typical mart responsibilities:

- expose stable fact and dimension models
- support analytics and filtering
- provide high-confidence tables for downstream consumers

## Planned fact models

### fact_matches

Purpose:

- represent clean match-level facts

Grain:

- one row per match

Possible fields:

- match_id
- event_id or event_name
- team1
- team2
- score1
- score2
- winning_team
- losing_team
- match_type
- match_date
- forfeit
- map_count
- data_complete

Use cases:

- recent match listings
- event-level match analysis
- team performance analysis

---

### fact_player_map_stats

Purpose:

- represent player performance facts at the player-map grain

Grain:

- one row per player per map

Possible fields:

- match_id
- map_id
- player_id
- team_name
- map_name
- event
- match_date
- kills
- deaths
- assists
- headshots
- kast
- adr
- rating
- kd_diff
- fk_diff

Use cases:

- player performance lookups
- player map splits
- rating and ADR trend analysis

---

### fact_player_match_stats

Purpose:

- represent player performance at the player-match grain

Grain:

- one row per player per match

Possible fields:

- match_id
- player_id
- player_name
- total_kills
- total_deaths
- total_assists
- avg_rating
- avg_adr
- avg_kast
- event
- match_date

Use cases:

- player match summaries
- player consistency analysis
- future player ranking models

---

## Planned dimension models

### dim_players

Purpose:

- represent stable player identity attributes

Possible fields:

- player_id
- player_name
- player_url
- real_name
- country
- current_team_name if derivable
- active_flag if derivable

Use cases:

- filtering by player
- joining player metadata to fact tables

---

### dim_teams

Purpose:

- represent stable team attributes

Possible fields:

- team_id
- team_name
- team_url

Use cases:

- filtering by team
- joining team metadata to fact tables

---

### dim_events

Purpose:

- represent unique event entities

Possible fields:

- event_id if available
- event_name
- first_seen_date
- last_seen_date

Use cases:

- event filtering
- event-level rollups

---

### dim_maps

Purpose:

- represent unique map names and map-related attributes

Possible fields:

- map_name
- active_pool_flag if later derived
- map_group if later derived

Use cases:

- map-based filtering and analytics

---

# 4. Snapshot Layer (SCD2)

Status: implemented (#130). One snapshot records player-to-team roster
membership history as a Slowly Changing Dimension Type 2, with a mart
dimension shaped on top of it for consumers.

## player_roster_history_snapshot

- Grain: one row per player-team membership interval, keyed by
  (player_id, dbt_valid_from).
- Source: `int_player_current_team`, which derives each player's current
  team as the team_name from their most recent map that recorded a team
  (the ingestion pipeline does not populate a roster table). The derivation
  is deterministic (map_date desc, map_id desc tie-break) so re-runs against
  unchanged sources cannot corrupt recorded history.
- Strategy: `check` on `team_name`, keyed on `player_id`. The source has no
  reliable roster-change timestamp, and a `timestamp` strategy keyed on map
  recency would open a new interval every time a player simply played
  another map.
- dbt manages `dbt_valid_from`, `dbt_valid_to`, and `dbt_scd_id`. Intervals
  are effective-dated from when a snapshot run observed the change, not
  backdated to the underlying map date; `observed_map_date` carries the
  match-data context. The first snapshot run seeds each player's current
  membership with `dbt_valid_from` equal to that run's timestamp.
- History is additive only. The snapshot never mutates ingestion outputs or
  existing marts, and it builds in the same database/schema as the models,
  so resetting the local database also resets locally recorded history.

Run it with `dbt snapshot`, or as part of `dbt build`, which orders it after
its source model automatically.

## dim_player_roster_history

- Grain: one row per player-team membership interval, keyed by
  (player_id, valid_from), with `roster_history_key` as the surrogate key
  for downstream joins.
- Presentation shaping over the snapshot only: renames `dbt_valid_from` /
  `dbt_valid_to` to `valid_from` / `valid_to`, adds the surrogate key, and
  flags the open interval with `is_current`.
- Player identity fields stay in `dim_players`; consumers join on
  `player_id` rather than duplicating them here.

Point-in-time query example (roster of a team as of a given date):

```sql
select
    roster.player_id,
    players.player_name
from dim_player_roster_history as roster
join dim_players as players
    on players.player_id = roster.player_id
where roster.team_name = 'Some Team'
  and roster.valid_from <= timestamp '2026-06-01'
  and (
      roster.valid_to > timestamp '2026-06-01'
      or roster.valid_to is null
  )
```

---

## Planned Directory Structure

The dbt project should follow a clear folder structure:

```text
dbt/
  models/
    staging/
    intermediate/
    marts/
  snapshots/
  tests/
  macros/
  seeds/
```

This keeps model responsibilities obvious and helps both humans and AI tools understand the transformation layer.

---

## Model Naming Conventions

Use these prefixes consistently:

- `stg_` for staging models
- `int_` for intermediate models
- `fact_` for fact tables
- `dim_` for dimension tables
- `_snapshot` suffix for snapshots

Rules:

- use descriptive names
- avoid vague names like `final_matches` or `cleaned_data`
- keep model names aligned to grain and purpose

---

## Materialization Strategy

Materialization can be adjusted later, but the likely default approach is:

### staging

- views initially

### intermediate

- views or tables depending on cost and reuse

### marts

- tables, or incremental models later if data volume justifies it

This should be decided after actual query patterns and table sizes are understood.

---

## Testing Strategy

Status: implemented (#113). Grain `unique`/`not_null` tests cover every
source table, staging model, intermediate model, and mart; `relationships`
tests cover the key joins (maps -> matches, player rows -> maps/matches, and
fact -> dim joins). Multi-column `(map_id, player_id)` grains use
`dbt_utils.unique_combination_of_columns` (see `dbt/packages.yml`; install
with `dbt deps`). Run everything with `dbt build`.

dbt tests should be added to ensure trust in transformed models.

### Core test types

- `not_null`
- `unique`
- `relationships`
- accepted values where appropriate

## Example testing goals

### stg_matches

- match_id is not null
- match_id is unique

### stg_maps

- map_id is not null
- map_id is unique
- match_id relates to stg_matches.match_id

### stg_players

- map_id is not null
- player_id is not null
- relationship to stg_maps.map_id exists

### dim_players

- player_id is unique
- player_id is not null

### fact_matches

- match_id is unique
- match_date is not null when available

---

## Documentation Goals

Status: implemented (#114). Every source table, model, and physical model
column has a description in the model yml, and the generated lineage graph
shows the intended layering: sources feed only the staging views, staging
feeds the intermediate model and the marts, and `fact_player_map_stats` is
built from `int_match_player_stats`. Generate and view the docs site with:

```sh
uv run dbt docs generate --project-dir dbt --profiles-dir dbt
uv run dbt docs serve --project-dir dbt --profiles-dir dbt
```

Run `dbt run` or `dbt build` first so the catalog reflects the built tables.
Generated output goes to `dbt/target/`, which is gitignored: docs are
generated on demand rather than committed or published, and project
documentation under `docs/architecture/` remains the source of truth for
architecture boundaries. dbt docs cover the transformation layer only.

dbt documentation should help explain:

- model purpose
- model grain
- important columns
- lineage between models

Each model should have:

- a short description
- important column descriptions
- tests defined where appropriate

This makes the project stronger both for maintainability and portfolio presentation.

---

## Relationship to the API Layer

The FastAPI application should eventually prefer querying trusted transformed tables where appropriate.

Examples:

- recent matches endpoint -> fact_matches
- player stats endpoint -> fact_player_map_stats or fact_player_match_stats
- team summaries -> fact_matches + dim_teams

This keeps transformation logic out of the API code and reinforces separation of concerns.

---

## Planned Rollout Order

dbt should be introduced now that lifecycle semantics, active-stage
responsibilities, and match/map/player grains are stable.

Recommended rollout order:

1. add dbt project scaffolding
2. create staging models for matches, maps, and players
3. add basic tests
4. create intermediate reusable joins
5. create fact and dimension marts
6. update API/data consumers to use trusted marts where appropriate

---

## Notes

- dbt is a transformation layer, not an ingestion tool
- dbt should not absorb application logic that belongs in Python services
- dbt should not be used to paper over unclear ingestion-state semantics
- keep staging models light and predictable
- push reusable joins into intermediate models
- expose only trusted, well-defined marts to downstream consumers
- demo-related dbt models will come later, after the demo pipeline exists
