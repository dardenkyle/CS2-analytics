"""
The `storage` package provides a centralized interface for all database-related
interactions including:

- Database connections and session management
- Scrape queue managers for matches, maps, and demos
- Data models representing persistent entities
"""

from .storage_models import Match, Player
from .db_instance import db

__all__ = [
    "db",
    "Match",
    "Player",
]
