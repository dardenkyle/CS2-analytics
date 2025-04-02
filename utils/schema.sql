-- Drop existing tables if they exist (for debugging purposes)
DROP TABLE IF EXISTS player_transfers,
player_aliases,
player_team_history,
players,
maps,
matches,
teams,
player_info;

-- ✅ Teams Table
CREATE TABLE teams (
    team_id INT PRIMARY KEY,
    team_name TEXT NOT NULL,
    team_url TEXT NOT NULL,
    region TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scraped_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    data_complete BOOLEAN
);

-- ✅ Player Info Table (Previously `players`)
CREATE TABLE player_info (
    player_id INT PRIMARY KEY,
    player_name TEXT NOT NULL,
    player_url TEXT NOT NULL,
    team_id INT REFERENCES teams(team_id) ON DELETE
    SET
        NULL,
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_scraped_at TIMESTAMP,
        last_updated_at TIMESTAMP,
        data_complete BOOLEAN
);

-- ✅ Matches Table
CREATE TABLE matches (
    match_id INT PRIMARY KEY,
    match_url TEXT UNIQUE NOT NULL,
    map_links TEXT,
    demo_links TEXT,
    team1 TEXT NOT NULL,
    team2 TEXT NOT NULL,
    score1 INT CHECK (score1 >= 0),
    score2 INT CHECK (score2 >= 0),
    winner TEXT NOT NULL CHECK (winner IN ('team1', 'team2')),
    event TEXT,
    match_type TEXT,
    forfeit BOOLEAN DEFAULT FALSE,
    date TIMESTAMP NOT NULL,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scraped_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    data_complete BOOLEAN
);

-- ✅ Maps Table (Previously `maps_played`)
CREATE TABLE maps (
    map_id INT PRIMARY KEY,
    match_id INT REFERENCES matches(match_id) ON DELETE CASCADE,
    map_order INT CHECK (
        map_order BETWEEN 1
        AND 5
    ),
    map_name TEXT NOT NULL,
    team1_score INT,
    team2_score INT,
    winner TEXT NOT NULL CHECK (winner IN ('team1', 'team2')),
    date TIMESTAMP NOT NULL,
    data_complete BOOLEAN DEFAULT TRUE
);

-- ✅ Players Table (Previously `players_stats`)  #################### Update this
CREATE TABLE players (
    match_id INT,
    map_id INT,
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
    kast FLOAT,
    kd_diff INT,
    adr FLOAT,
    fk_diff INT,
    rating FLOAT,
    data_complete BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (map_id, player_id)
);

-- ✅ Player Team History Table (Tracks past teams)
CREATE TABLE player_team_history (
    id SERIAL PRIMARY KEY,
    player_id INT REFERENCES player_info(player_id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    team_id INT REFERENCES teams(team_id) ON DELETE
    SET
        NULL,
        team_name TEXT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE,
        inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(player_id, team_id, start_date)
);

-- ✅ Player Aliases Table (Tracks name changes)
CREATE TABLE player_aliases (
    id SERIAL PRIMARY KEY,
    player_id INT REFERENCES player_info(player_id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ✅ Player Transfers Table (Tracks when players move between teams)
CREATE TABLE player_transfers (
    transfer_id SERIAL PRIMARY KEY,
    player_id INT REFERENCES player_info(player_id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    old_team_id INT REFERENCES teams(team_id) ON DELETE
    SET
        NULL,
        old_team_name TEXT NOT NULL,
        new_team_id INT REFERENCES teams(team_id) ON DELETE
    SET
        NULL,
        new_team_name TEXT NOT NULL,
        transfer_date DATE NOT NULL
);

-- ✅ Match Scrape Queue Table
-- This table is used to track the scraping status of matches.
CREATE TABLE match_scrape_queue (
    match_id INT PRIMARY KEY,
    -- Same as match_id from HLTV
    match_url TEXT UNIQUE NOT NULL,
    STATUS TEXT NOT NULL DEFAULT 'pending',
    -- pending, success, failed, skipped
    retries INT DEFAULT 0,
    error TEXT,
    -- Optional: last error message or traceback
    last_attempt TIMESTAMP,
    next_attempt TIMESTAMP,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ✅ Map Scrape Queue Table
-- This table is used to track the scraping status of maps.
CREATE TABLE map_scrape_queue (
    map_id INT PRIMARY KEY,
    map_url TEXT NOT NULL,
    STATUS TEXT DEFAULT 'pending',
    -- pending, success, failed
    retries INT DEFAULT 0,
    last_attempt TIMESTAMP,
    error TEXT
);

-- ✅ Demo Files Table
-- This table is used to track the status of demo files.
CREATE TABLE demo_files (
    map_id INT PRIMARY KEY REFERENCES maps(map_id) ON DELETE CASCADE,
    demo_url TEXT NOT NULL,
    local_path TEXT,
    parsed BOOLEAN DEFAULT FALSE,
    heatmap_done BOOLEAN DEFAULT FALSE,
    grenade_analysis_done BOOLEAN DEFAULT FALSE,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_processed_at TIMESTAMP
);

-- ✅ Scraper history table
-- This table is used to track the history of scrape runs.
CREATE TABLE scrape_runs (
    run_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_matches INT,
    matches_success INT,
    matches_failed INT,
    notes TEXT
);

-- ✅ Player Metrics Table
-- This table is used to store player performance metrics.
CREATE TABLE player_metrics (
    player_id INT,
    map_name TEXT,
    average_kills FLOAT,
    entry_rating FLOAT,
    clutch_success_rate FLOAT,
    matches_played INT,
    last_updated TIMESTAMP,
    PRIMARY KEY (player_id, map_name)
);

-- ✅ Indexes for Performance Optimization
CREATE INDEX idx_matches_date ON matches (date);

CREATE INDEX idx_maps_match_id ON maps (match_id);

CREATE INDEX idx_players_map_id ON players (map_id);

CREATE INDEX idx_players_player_id ON players(player_id);

CREATE INDEX idx_player_info_team_id ON player_info (team_id);

CREATE INDEX idx_player_transfers_player_id ON player_transfers (player_id);

CREATE INDEX idx_player_team_history_player_id ON player_team_history (player_id);