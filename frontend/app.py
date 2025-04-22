"""
Streamlit debug app to visually verify top players from CS2 Analytics API.
"""

import streamlit as st
import requests


def fetch_top_players(min_maps: int = 5, limit: int = 10) -> list[dict]:
    """
    Fetches top players from the FastAPI backend.

    Args:
        min_maps (int): Minimum number of maps played.
        limit (int): Number of top players to retrieve.

    Returns:
        list[dict]: List of player stats.
    """
    url = "http://localhost:8000/api/top_players"
    params = {"min_maps": min_maps, "limit": limit}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return []


st.title("🔍 CS2 Top Player Debug View")

min_maps = st.slider("Minimum Maps", 1, 50, 5)
limit = st.slider("Number of Players", 1, 50, 10)

if st.button("Fetch Top Players"):
    players = fetch_top_players(min_maps, limit)
    if players:
        st.success("✅ Data retrieved successfully.")
        st.dataframe(players)
    else:
        st.warning("No data returned.")
