import streamlit as st
import pandas as pd
import requests

# Config
API_URL = "http://localhost:8000/api/top_players"

# Page setup
st.set_page_config(page_title="Top CS2 Players", layout="centered")
st.title("🔝 Top CS2 Players by Average Rating")

# User filter
min_maps = st.slider("Minimum Maps Played", min_value=1, max_value=20, value=5)


@st.cache_data
def get_top_players(min_maps: int) -> pd.DataFrame:
    """
    Fetch top players by average rating from FastAPI backend.
    """
    try:
        response = requests.get(f"{API_URL}?min_maps={min_maps}")
        response.raise_for_status()
        data = response.json()

        # Handle backend errors
        if isinstance(data, dict) and "error" in data:
            st.error(f"❌ Backend error: {data['error']}")
            return pd.DataFrame()

        if not isinstance(data, list):
            st.error("❌ Unexpected response format from backend.")
            return pd.DataFrame()

        return pd.DataFrame(data)

    except requests.RequestException as e:
        st.error(f"❌ Failed to connect to backend: {e}")
        return pd.DataFrame()


# Fetch and display
df = get_top_players(min_maps)

if not df.empty:
    st.dataframe(df, use_container_width=True)
    st.bar_chart(df.set_index("player_name")["avg_rating"])
else:
    st.info("No data available for the selected filter.")
