# Database Schema

This document is split into two parts:

- Current schema: what exists today in `cs2_analytics/storage/schema.sql`
- Planned schema direction: candidates for lifecycle cleanup, dbt, and later orchestration

Current intent:

- `cs2_analytics/storage/schema.sql` remains the source of truth for the current implementation.
- The next schema work should focus on lifecycle semantics for match and map discovery before dbt or Airflow is added.

---

## Current Schema (Source of Truth)

Use `cs2_analytics/storage/schema.sql` as final authority.
Treat this as the working contract for the current codebase.

### Core tables

#### `matches`

- `match_id` (PK)
- `match_url` (unique)
- `map_links`, `demo_links`
- `team1`, `team2`, `score1`, `score2`, `winner`
- `event`, `match_type`, `forfeit`, `date`
- `last_inserted_at`, `last_scraped_at`, `last_updated_at`
- `data_complete`

#### `maps`

- `map_id` (PK)
- `match_id` (FK -> `matches.match_id`)
- `map_order`, `map_name`, `team1_score`, `team2_score`, `winner`, `date`
- `data_complete`

#### `players`

Grain: one row per player per map.

- `map_id`, `player_id` (composite PK)
- `player_name`, `player_url`, `map_name`, `team_name`
- `kills`, `headshots`, `assists`, `flash_assists`, `deaths`
- `traded_deaths`, `opening_kills`, `opening_deaths`, `multi_kills`, `clutches_won`
- `kast`, `kd_diff`, `adr`, `fk_diff`, `round_swing`, `rating`
- `last_inserted_at`, `last_scraped_at`, `last_updated_at`
- `data_complete`

#### `teams`

- `team_id` (PK)
- `team_name`, `team_url`, `region`
- `created_at`, `last_scraped_at`, `last_updated_at`
- `data_complete`

#### `player_info`

- `player_id` (PK)
- `player_name`, `player_url`
- `team_id` (FK -> `teams.team_id`)
- `active`
- `created_at`, `last_scraped_at`, `last_updated_at`
- `data_complete`

#### `player_aliases`

- `id` (PK)
- `player_id` (FK -> `player_info.player_id`)
- `alias`, `changed_at`

#### `player_team_history`

- `id` (PK)
- `player_id` (FK -> `player_info.player_id`)
- `team_id` (FK -> `teams.team_id`)
- `player_name`, `team_name`, `start_date`, `end_date`
- `last_inserted_at`

#### `player_transfers`

- `transfer_id` (PK)
- `player_id` (FK -> `player_info.player_id`)
- `player_name`
- `old_team_id`, `old_team_name`
- `new_team_id`, `new_team_name`
- `transfer_date`

### Current ingestion and discovery tables

The current code uses queue-oriented names:

- `match_scrape_queue`
- `map_scrape_queue`
- `demo_scrape_queue`

For match and map processing, those tables are no longer best thought of as simple transient queues. They are increasingly acting as lifecycle/state tables for discovered entities.

That means they should eventually describe:

- when an entity was first discovered
- when it was last seen in discovery
- whether it is ready for processing
- whether processing was attempted
- whether it succeeded or failed
- what run or worker last touched it

The existing code still uses the current table names, so this document uses those names when referring to the present implementation.

#### `match_scrape_queue`

- Current role in code: tracks discovered match work items
- Intended direction: lifecycle/state table for discovered matches
- Future-state naming candidate: `match_ingestion_state`

#### `map_scrape_queue`

- Current role in code: tracks discovered map work items
- Intended direction: lifecycle/state table for discovered maps
- Future-state naming candidate: `map_ingestion_state`

#### `demo_scrape_queue`

- Current role in code: tracks demo work items
- Notes: this table remains closer to a true work queue until the demo stage is designed more fully

### Demo-processing support tables

#### `demo_files`

- `map_id` (PK, FK -> `maps.map_id`)
- `demo_url`, `local_path`
- `parsed`, `heatmap_done`, `grenade_analysis_done`
- `last_inserted_at`, `last_processed_at`

### Operational and analytics support tables

#### `scrape_runs`

- `run_id` (PK)
- `started_at`, `ended_at`
- `total_matches`, `matches_success`, `matches_failed`
- `notes`

#### `player_metrics`

- `player_id`, `map_name` (composite PK)
- `average_kills`, `entry_rating`, `clutch_success_rate`, `matches_played`
- `last_updated_at`

---

## Lifecycle and Audit Field Guidance

Lifecycle fields should only exist when they carry a distinct meaning. Do not add multiple timestamps that all mean "the last time something happened."

Recommended field meanings:

- `status`
  Current lifecycle state for the entity. The exact value set should reflect real processing semantics, not only queue semantics.
- `first_seen_at`
  When the entity was first discovered.
- `last_seen_at`
  Most recent time the discovery stage saw the entity again.
- `last_attempted_at`
  Most recent time a processing stage began or attempted work on the entity.
- `last_processed_at`
  Most recent time processing completed successfully.
- `last_failed_at`
  Most recent time processing ended in failure.
- `retry_count`
  Count of retry attempts for the current processing model.
- `failure_count`
  Count of distinct failures over the lifetime of the row.
- `last_error_message`
  Most recent normalized failure message.
- `run_id`
  Identifier for the pipeline run or orchestration run that last touched the row.
- `worker_id`
  Identifier for the worker or process that last touched the row when that distinction matters.
- `inserted_at`
  Row creation timestamp.
- `last_updated_at`
  Most recent timestamp for any meaningful row update.

Field selection guidance:

- Prefer `inserted_at` over multiple variants of row-creation timestamps.
- Prefer `last_updated_at` as the generic row-change timestamp.
- Add `last_attempted_at`, `last_processed_at`, and `last_failed_at` only if each one is used distinctly.
- Add `run_id` and `worker_id` only when run-level tracing or multi-worker semantics actually need them.
- Prefer `last_error_message` over vague names such as `last_error` when the field stores normalized message text.

---

## Planned Schema Direction

The following items are planned, but they should follow lifecycle review and active-stage cleanup.

### Planned lifecycle-state cleanup

- Clarify status values based on lifecycle semantics, not only queue semantics
- Add only distinct audit fields
- Revisit whether current table names still fit their purpose
- Keep naming changes secondary to semantic clarity

### Planned raw-layer tables

- `raw_matches`
- `raw_maps`

Planned purpose:

- store raw page snapshots or metadata for reproducibility and parser debugging
- support replay or reprocessing workflows when that need becomes concrete

### Planned transform layer

Planned dbt model families:

- staging (`stg_*`)
- intermediate (`int_*`)
- marts (`fact_*`, `dim_*`)

See `docs/dbt_models.md` for later-phase dbt planning.

---

## Notes

- Do not assume planned tables or fields exist until they are added to `schema.sql`.
- Treat current table names and future semantic roles separately.
- For implementation work, align code and docs to the current section above first.
