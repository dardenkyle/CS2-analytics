"""
The `storage` package provides a centralized interface for all database-related
interactions including:

- Database connections and session management
- Database connection helpers and persistence modules
- Data models representing persistent entities
"""

from .db_instance import db

__all__ = [
    "db",
    "Match",
    "Player",
]
