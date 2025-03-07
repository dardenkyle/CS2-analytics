import psycopg2

# ✅ Change to match your PostgreSQL setup
DB_NAME = "cs2_db"
DB_USER = "postgres"
DB_PASS = "gE=XG'99"  # Update with your actual password
DB_HOST = "localhost"
DB_PORT = "5433"

def connect_db():
    """Connects to PostgreSQL database."""
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    print("✅ Successfully connected to postgreSQL database.")
    return conn, conn.cursor()

def ensure_tables():
    """Creates or updates the database schema automatically."""
    conn, cur = connect_db()

    cur.execute("drop table if exists matches, player_stats cascade")             # Delete tables if they exist to simplify debugging, can remove later

    # ✅ Create `matches` table if it does not exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id SERIAL PRIMARY KEY,
        match_url TEXT UNIQUE,
        team1 TEXT,
        team2 TEXT,
        score1 INT,
        score2 INT,
        event TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

        # ✅ Create `player_stats` table with `match_id` as a Foreign Key
    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_stats (
        -- player_id SERIAL PRIMARY KEY,
        match_id INT REFERENCES matches(match_id) ON DELETE CASCADE,
        player_name TEXT PRIMARY KEY,
        -- team TEXT,
        kills INT,
        headshots INT,     -- ✅ New Column
        assists INT,
        flash_assists INT, -- ✅ New Column
        deaths INT,
        kast float,
        kd_diff INT,
        adr FLOAT,
        fk_diff INT,
        rating FLOAT
    );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database schema ensured: Tables are up-to-date.")

if __name__ == "__main__":
    ensure_tables()  # Run this when script starts
