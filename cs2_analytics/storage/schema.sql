-- Teams Table
CREATE TABLE IF NOT EXISTS teams (
    team_id INT PRIMARY KEY,
    team_name TEXT NOT NULL,
    team_url TEXT NOT NULL,
    region TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scraped_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    data_complete BOOLEAN
);

-- Player Info Table (Previously `players`)
CREATE TABLE IF NOT EXISTS player_info (
    player_id INT PRIMARY KEY,
    player_name TEXT NOT NULL,
    player_url TEXT NOT NULL,
    team_id INT REFERENCES teams(team_id) ON DELETE SET NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scraped_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    data_complete BOOLEAN
);

-- Matches Table
CREATE TABLE IF NOT EXISTS matches (
    match_id INT PRIMARY KEY,
    match_url TEXT UNIQUE NOT NULL,
    map_links TEXT,
    demo_links TEXT,
    team1 TEXT NOT NULL,
    team2 TEXT NOT NULL,
    score1 INT CHECK (score1 >= 0),
    score2 INT CHECK (score2 >= 0),
    winner TEXT NOT NULL CHECK (
        winner = team1
        OR winner = team2
    ),
    event TEXT,
    match_type TEXT,
    forfeit BOOLEAN DEFAULT FALSE,
    date TIMESTAMP NOT NULL,
    last_inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scraped_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    data_complete BOOLEAN
);

-- Maps Table (Previously `maps_played`)
CREATE TABLE IF NOT EXISTS maps (
    map_id INT PRIMARY KEY,
    match_id INT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    map_url TEXT UNIQUE NOT NULL,
    map_order INT NOT NULL CHECK (
        map_order BETWEEN 1
        AND 5
    ),
    map_name TEXT NOT NULL,
    team1_score INT NOT NULL CHECK (team1_score >= 0),
    team2_score INT NOT NULL CHECK (team2_score >= 0),
    map_winner TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    inserted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_scraped_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ,
    data_complete BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (match_id, map_order)
);

-- Players Table (Previously `players_stats`)
CREATE TABLE IF NOT EXISTS players (
    map_id INT NOT NULL REFERENCES maps(map_id) ON DELETE CASCADE,
    player_id INT,
    player_name TEXT NOT NULL,
    player_url TEXT,
    map_name TEXT NOT NULL,
    team_name TEXT,
    kills INT,
    headshots INT,
    assists INT,
    flash_assists INT,
    deaths INT,
    traded_deaths INT,
    opening_kills INT,
    opening_deaths INT,
    multi_kills INT,
    clutches_won INT,
    kast FLOAT,
    kd_diff INT,
    adr FLOAT,
    fk_diff INT,
    round_swing FLOAT,
    rating FLOAT,
    last_inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scraped_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    data_complete BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (map_id, player_id)
);

-- Player Team History Table (Tracks past teams)
CREATE TABLE IF NOT EXISTS player_team_history (
    id SERIAL PRIMARY KEY,
    player_id INT REFERENCES player_info(player_id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    team_id INT REFERENCES teams(team_id) ON DELETE SET NULL,
    team_name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    last_inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, team_id, start_date)
);

-- Player Aliases Table (Tracks name changes)
CREATE TABLE IF NOT EXISTS player_aliases (
    id SERIAL PRIMARY KEY,
    player_id INT REFERENCES player_info(player_id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Player Transfers Table (Tracks when players move between teams)
CREATE TABLE IF NOT EXISTS player_transfers (
    transfer_id SERIAL PRIMARY KEY,
    player_id INT REFERENCES player_info(player_id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    old_team_id INT REFERENCES teams(team_id) ON DELETE SET NULL,
    old_team_name TEXT NOT NULL,
    new_team_id INT REFERENCES teams(team_id) ON DELETE SET NULL,
    new_team_name TEXT NOT NULL,
    transfer_date DATE NOT NULL
);

-- Match Ingestion State Table
-- Tracks discovery and processing lifecycle for matches.
CREATE TABLE IF NOT EXISTS match_ingestion_state (
    match_id INT PRIMARY KEY,
    match_url TEXT NOT NULL,
    status TEXT CHECK (
        status IN ('pending', 'processing', 'processed', 'failed', 'skipped')
    ) NOT NULL DEFAULT 'pending',
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_attempted_at TIMESTAMP,
    last_processed_at TIMESTAMP,
    last_failed_at TIMESTAMP,
    failure_count INT NOT NULL DEFAULT 0,
    last_error_message TEXT,
    source TEXT,
    priority INT DEFAULT 0,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Map Ingestion State Table
-- Tracks discovery and processing lifecycle for maps.
CREATE TABLE IF NOT EXISTS map_ingestion_state (
    map_id INT PRIMARY KEY,
    map_url TEXT NOT NULL,
    match_id INT REFERENCES matches(match_id) ON DELETE CASCADE,
    map_order INT CHECK (
        map_order BETWEEN 1
        AND 5
    ),
    status TEXT CHECK (
        status IN ('pending', 'processing', 'processed', 'failed', 'skipped')
    ) NOT NULL DEFAULT 'pending',
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_attempted_at TIMESTAMP,
    last_processed_at TIMESTAMP,
    last_failed_at TIMESTAMP,
    failure_count INT NOT NULL DEFAULT 0,
    last_error_message TEXT,
    source TEXT,
    priority INT DEFAULT 0,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Demo Ingestion State Table
CREATE TABLE IF NOT EXISTS demo_ingestion_state (
    demo_id TEXT PRIMARY KEY,
    demo_url TEXT NOT NULL,
    status TEXT CHECK (
        status IN ('pending', 'processing', 'processed', 'failed', 'skipped')
    ) NOT NULL DEFAULT 'pending',
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_attempted_at TIMESTAMP,
    last_processed_at TIMESTAMP,
    last_failed_at TIMESTAMP,
    failure_count INT NOT NULL DEFAULT 0,
    last_error_message TEXT,
    source TEXT,
    priority INT DEFAULT 0,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- This table is used to track the status of demo files.
CREATE TABLE IF NOT EXISTS demo_files (
    map_id INT PRIMARY KEY REFERENCES maps(map_id) ON DELETE CASCADE,
    demo_url TEXT NOT NULL,
    local_path TEXT,
    parsed BOOLEAN DEFAULT FALSE,
    heatmap_done BOOLEAN DEFAULT FALSE,
    grenade_analysis_done BOOLEAN DEFAULT FALSE,
    last_inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_processed_at TIMESTAMP
);

-- Scraper history table
-- This table is used to track the history of scrape runs.
CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_matches INT,
    matches_success INT,
    matches_failed INT,
    notes TEXT
);

-- Player Metrics Table
-- This table is used to store player performance metrics.
CREATE TABLE IF NOT EXISTS player_metrics (
    player_id INT,
    map_name TEXT,
    average_kills FLOAT,
    entry_rating FLOAT,
    clutch_success_rate FLOAT,
    matches_played INT,
    last_updated_at TIMESTAMP,
    PRIMARY KEY (player_id, map_name)
);
