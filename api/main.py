"""This is the FastAPI application for the CS2 Analytics API.
It provides endpoints to retrieve player statistics and other data."""

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from cs2_analytics.storage.database import Database


app = FastAPI()

# Allow frontend (Streamlit) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only; tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()


@app.get("/api/top_players")
def get_top_players(min_maps: int = Query(5, ge=1), limit: int = Query(10, le=100)):
    """
    Returns top players by average rating.
    """
    sql = """
        SELECT
            player_name,
            COUNT(*) AS maps_played,
            ROUND(AVG(rating)::numeric, 2) AS avg_rating
        FROM players
        GROUP BY player_name
        HAVING COUNT(*) >= %s
        ORDER BY avg_rating DESC
        LIMIT %s;
    """
    try:
        with db.get_cursor() as cur:
            cur.execute(sql, (min_maps, limit))
            rows = cur.fetchall()
            if not rows:
                return []

            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]  # ✅ Safe list of dicts
    except Exception as e:
        print(f"❌ DB error: {e}")
        return {"error": str(e)}
