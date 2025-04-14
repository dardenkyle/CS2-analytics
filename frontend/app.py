"""This is the frontend application for the CS2 Top Players API during development."""

import streamlit as st
import requests

BASE_URL = "http://localhost:8000/api"

st.title("CS2 Top Players")

rating_threshold = st.slider("Minimum Rating", 1.0, 2.0, 1.2)

try:
    response = requests.get(
        f"{BASE_URL}/top_players", params={"min_rating": rating_threshold}
    )
    response.raise_for_status()
    data = response.json()
    st.dataframe(data)
except requests.RequestException as e:
    st.error(f"Failed to fetch data: {e}")
