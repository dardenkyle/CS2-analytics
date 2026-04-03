# Database Schema

This document is split into two parts:

- Current schema: what exists today in `cs2_analytics/storage/schema.sql`
- Planned schema: candidates for the dbt era and future pipeline expansion

Current intent:

- The schema is good enough for current pipeline work.
- Full schema lock-down is deferred until after hardening/stabilization milestones.

---

## Current Schema (Source of Truth)

Use `cs2_analytics/storage/schema.sql` as final authority.
Treat this as the working contract for now (stable enough, not yet final-frozen).

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

### Queue tables (current standard)

Current queue status values:

- `queued`
- `parsed`
- `failed`

Current queue metadata fields:

- `last_inserted_at`
- `last_updated_at`
- `retry_count`
- `last_error`
- `priority`
- `source`

#### `match_scrape_queue`

- `match_id` (PK), `match_url`, status + metadata above

#### `map_scrape_queue`

- `map_id` (PK), `map_url`, status + metadata above

#### `demo_scrape_queue`

- `demo_id` (PK), `demo_url`, status + metadata above

### Demo-processing support tables

#### `demo_files`

- `map_id` (PK, FK -> `maps.map_id`)
- `demo_url`, `local_path`
- `parsed`, `heatmap_done`, `grenade_analysis_done`
- `last_inserted_at`, `last_processed_at`

### Operational/analytics support tables

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

## Planned Schema (Post-Hardening / dbt era)

The following items are intentionally planned and are expected to be introduced around the time dbt is implemented and transformation needs are clearer.

### Planned raw-layer tables

- `raw_matches`
- `raw_maps`

Planned purpose:

- store raw page snapshots/metadata for reproducibility and parser debugging
- support replay/reprocessing workflows

### Planned queue enhancements

Potential future additions (not current standard):

- statuses like `processing`/`completed`
- lock fields (`locked_at`, `locked_by`)
- retry scheduling (`available_at`)
- safe claiming semantics (`FOR UPDATE SKIP LOCKED`)

### Planned transform layer

Planned dbt model families:

- staging (`stg_*`)
- intermediate (`int_*`)
- marts (`fact_*`, `dim_*`)

See `docs/dbt_models.md` for detailed dbt planning.

---

## Notes

- Do not assume planned tables/fields exist until they are added to `schema.sql`.
- For implementation work, align code and docs to the current section above.
