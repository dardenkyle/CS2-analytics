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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ✅ Player Info Table (Previously `players`)
CREATE TABLE player_info (
    player_id INT PRIMARY KEY,
    player_name TEXT NOT NULL,
    player_url TEXT NOT NULL,
    team_id INT REFERENCES teams(team_id) ON DELETE
    SET
        NULL,
        team_name TEXT,
        active BOOLEAN DEFAULT TRUE
);

-- ✅ Matches Table
CREATE TABLE matches (
    match_id INT PRIMARY KEY,
    match_url TEXT UNIQUE NOT NULL,
    map_links TEXT,
    demo_links TEXT,
    team1 TEXT NOT NULL,
    team2 TEXT NOT NULL,
    score1 INT,
    score2 INT,
    event TEXT,
    match_type TEXT,
    forfeit BOOLEAN DEFAULT FALSE,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_complete BOOLEAN
);

-- ✅ Maps Table (Previously `maps_played`)
CREATE TABLE maps (
    map_id_id INT PRIMARY KEY,
    match_id INT REFERENCES matches(match_id) ON DELETE CASCADE,
    map_name TEXT NOT NULL,
    map_order INT CHECK (
        map_order BETWEEN 1
        AND 5
    ),
    team1_score INT,
    team2_score INT,
    winner TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        end_date TEXT DEFAULT 'Currently Active'
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

-- ✅ Indexes for Performance Optimization
CREATE INDEX idx_matches_date ON matches (date);

CREATE INDEX idx_maps_match_id ON maps (match_id);

CREATE INDEX idx_players_map_id ON players (map_id);

CREATE INDEX idx_player_info_team_id ON player_info (team_id);

CREATE INDEX idx_player_transfers_player_id ON player_transfers (player_id);

CREATE INDEX idx_player_team_history_player_id ON player_team_history (player_id);