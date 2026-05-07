# Intended Schema Target

This is the intended parsed-source schema target before implementing dbt.
It belongs to Phase 3.5 and should stabilize match, map, and player source
tables before dbt models are added.

`cs2_analytics/storage/schema.sql` remains the source of truth until this target
is implemented.

## Audit Field Convention

These parsed source tables use the same audit fields:

- `inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
- `last_scraped_at TIMESTAMP`
- `last_updated_at TIMESTAMP`
- `data_complete BOOLEAN`

Field meanings:

- `inserted_at`: first persistence timestamp for this source row. Upserts should
  preserve it.
- `last_scraped_at`: most recent time the source page or parsed record was
  scraped for this row.
- `last_updated_at`: most recent meaningful database update to this row.
- `data_complete`: whether the parsed source row has the fields needed for
  downstream relational/dbt use.

Do not copy ingestion-state lifecycle fields such as `first_seen_at`,
`last_seen_at`, `last_attempted_at`, `last_processed_at`, `last_failed_at`,
`failure_count`, or `last_error_message` into these parsed source tables. Those
belong in `*_ingestion_state`.

The current implementation still uses `last_inserted_at` in storage models.
Renaming it to `inserted_at` should be handled in the focused Phase 3.5 schema,
model, storage, and test update that implements this target.

## matches

- match_id INT PRIMARY KEY
- match_url TEXT UNIQUE NOT NULL
- team1 TEXT NOT NULL
- team2 TEXT NOT NULL
- score1 INT CHECK (score1 >= 0)
- score2 INT CHECK (score2 >= 0)
- winner TEXT NOT NULL CHECK (winner = team1 OR winner = team2)
- event TEXT
- match_type TEXT
- forfeit BOOLEAN DEFAULT FALSE
- date TIMESTAMP NOT NULL
- map_links JSONB or TEXT -- trace/debug only, dbt ignores this
- demo_links JSONB or TEXT -- trace/debug only, dbt ignores this
- inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- last_scraped_at TIMESTAMP
- last_updated_at TIMESTAMP
- data_complete BOOLEAN DEFAULT FALSE

## maps

- map_id INT PRIMARY KEY -- HLTV mapstatsid, e.g. 228300
- match_id INT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE
- map_url TEXT UNIQUE NOT NULL
- map_order INT NOT NULL CHECK (map_order BETWEEN 1 AND 5)
- map_name TEXT NOT NULL
- team1_score INT NOT NULL CHECK (team1_score >= 0)
- team2_score INT NOT NULL CHECK (team2_score >= 0)
- winner TEXT NOT NULL CHECK (winner IN ('team1', 'team2'))
- date TIMESTAMP NOT NULL
- inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- last_scraped_at TIMESTAMP
- last_updated_at TIMESTAMP
- data_complete BOOLEAN DEFAULT FALSE
- UNIQUE (match_id, map_order)

## players

- map_id INT NOT NULL REFERENCES maps(map_id) ON DELETE CASCADE
- player_id INT NOT NULL
- player_name TEXT NOT NULL
- player_url TEXT
- map_name TEXT NOT NULL -- parsed context; dbt should prefer maps.map_name
- team_name TEXT NOT NULL
- team_side TEXT CHECK (team_side IN ('team1', 'team2')) -- strongly recommended
- kills INT
- headshots INT
- assists INT
- flash_assists INT
- deaths INT
- traded_deaths INT
- opening_kills INT
- opening_deaths INT
- multi_kills INT
- clutches_won INT
- kast FLOAT
- kd_diff INT
- adr FLOAT
- fk_diff INT
- round_swing FLOAT
- rating FLOAT
- inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- last_scraped_at TIMESTAMP
- last_updated_at TIMESTAMP
- data_complete BOOLEAN DEFAULT FALSE
- PRIMARY KEY (map_id, player_id)

## Deferred Schema Candidates

The saved HLTV map stats page shows additional player stat variants that are
available but intentionally outside this immediate Phase 3.5 target.

### Side-split player stats

The map stats page exposes `totalstats`, `ctstats`, and `tstats` tables.
The immediate target keeps `players` at one row per player per map using total
stats only. CT/T splits should be added later only after the base
`matches -> maps -> players` contract is stable.

Likely future grain:

- one row per player per map per stat scope
- `stat_scope TEXT CHECK (stat_scope IN ('total', 'ct', 't'))`

### Eco-adjusted stats

The map stats page also exposes hidden eco-adjusted values:

- opening eco-adjusted kills/deaths
- eco-adjusted kills
- eco-adjusted deaths
- eco-adjusted traded deaths
- eco-adjusted ADR
- eco-adjusted KAST

These should not be added to the immediate `players` table target yet. When
implemented, prefer a focused parser/storage/schema branch that decides whether
eco-adjusted values belong as columns on a side-scoped player stats table or in
a separate metric-variant table.

### Map player highlights

The map page includes top summary boxes such as most kills, most damage, most
assists, most AWP kills, most first kills, and best rating. These are
player-derived map highlights rather than map identity fields, so they should
not be added directly to `maps`.

If retained, prefer a separate table such as:

- `map_id`
- `highlight_type`
- `player_id`
- `player_name`
- `value`
- `rank`
