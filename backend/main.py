"""Docstring for main.py module.
This module contains the FastAPI application for the CSs player rating API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow Streamlit frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/top_players")
def get_top_players(min_rating: float = 1.2):
    return [{"player": "s1mple", "rating": 1.35}, {"player": "ZywOo", "rating": 1.32}]
