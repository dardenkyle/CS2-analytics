# Database Schema

This document is split into two parts:

- Current schema: what exists today in Alembic and `cs2_analytics/storage/schema.sql`
- Planned schema direction: candidates for follow-up schema cleanup, dbt, and
  later orchestration

Current intent:

- Alembic migrations own application/source schema for setup and deployment.
- `cs2_analytics/storage/schema.sql` remains a readable reference for the current
  implementation and should stay aligned with migrations during the transition.
- The ingestion-state lifecycle schema is implemented.
- Active match, map, and demo controllers delegate per-item workflow to stage
  services; the next major architecture phase is dbt.

---

## Current Schema Reference

Use the initial Alembic migration as the executable setup path. Treat
`cs2_analytics/storage/schema.sql` as the readable schema reference for the
current codebase.

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
- `map_url` (unique)
- `map_order`, `map_name`, `team1_score`, `team2_score`, `map_winner`, `date`
- `inserted_at`, `last_scraped_at`, `last_updated_at`
- `data_complete`
- Unique constraint: `match_id`, `map_order`

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

The current code uses ingestion-state names:

- `match_ingestion_state`
- `map_ingestion_state`
- `demo_ingestion_state`

For match and map processing, those tables are lifecycle/state tables for discovered entities rather than simple transient queues.

They describe:

- when an entity was first discovered
- when it was last seen in discovery
- whether it is ready for processing
- whether processing was attempted
- whether it succeeded or failed
- the latest failure or skipped reason, when applicable

#### `match_ingestion_state`

- Current role in code: tracks discovered match lifecycle state
- Primary key: `match_id`
- URL field: `match_url`
- Lifecycle fields: `status`, `first_seen_at`, `last_seen_at`, `last_attempted_at`, `last_processed_at`, `last_failed_at`, `failure_count`, `last_error_message`, `source`, `priority`, `last_updated_at`

#### `map_ingestion_state`

- Current role in code: tracks discovered map lifecycle state
- Primary key: `map_id`
- URL field: `map_url`
- Parent context fields: `match_id`, `map_order`
- Lifecycle fields: `status`, `first_seen_at`, `last_seen_at`, `last_attempted_at`, `last_processed_at`, `last_failed_at`, `failure_count`, `last_error_message`, `source`, `priority`, `last_updated_at`

#### `demo_ingestion_state`

- Current role in code: tracks discovered demo lifecycle state
- Primary key: `demo_id`
- URL field: `demo_url`
- Lifecycle fields: `status`, `first_seen_at`, `last_seen_at`, `last_attempted_at`, `last_processed_at`, `last_failed_at`, `failure_count`, `last_error_message`, `source`, `priority`, `last_updated_at`
- Notes: demo processing remains deferred even though the lifecycle table naming is aligned

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
- `failure_count`
  Count of distinct failures over the lifetime of the row.
- `last_error_message`
  Most recent normalized failure message.
- `last_updated_at`
  Most recent timestamp for any meaningful row update.

Field selection guidance:

- Use `first_seen_at` as the discovery timestamp and `last_seen_at` for rediscovery refreshes.
- Prefer `last_updated_at` as the generic row-change timestamp.
- Keep `last_attempted_at`, `last_processed_at`, and `last_failed_at` distinct because each carries different lifecycle meaning.
- Avoid `retry_count`, `run_id`, and `worker_id` until orchestration or multi-worker behavior actually requires them.
- Prefer `last_error_message` over vague names such as `last_error` when the field stores normalized message text.

---

## Planned Schema Direction

The following items are planned, but they should follow the completed active
stage-service and dbt-readiness cleanup.

### Completed lifecycle-state cleanup

- Status values are based on lifecycle semantics: `pending`, `processing`, `processed`, `failed`, and `skipped`
- Ingestion-state tables use distinct lifecycle fields such as `first_seen_at`, `last_seen_at`, `last_attempted_at`, `last_processed_at`, and `last_failed_at`
- Current table names are `match_ingestion_state`, `map_ingestion_state`, and `demo_ingestion_state`
- Redundant fields such as `retry_count`, `run_id`, and `worker_id` are intentionally absent from these lifecycle tables

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

- Do not assume planned tables or fields exist until they are added to Alembic
  migrations and the schema reference.
- Treat current table names and future semantic roles separately.
- For implementation work, align code and docs to the current section above first.
