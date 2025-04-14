"""
Configuration module for CS2 Analytics.

This file ensures that configuration settings from `config.py` are easily accessible 
throughout the project without needing direct imports.
"""

from .config import (
    DB_NAME,
    DB_USER,
    DB_PASS,
    DB_HOST,
    DB_PORT,
    START_DATE,
    END_DATE,
    DEBUG_MODE,
    MAX_MATCHES,
    ENABLE_DEMO_DOWNLOADS,
    ENABLE_DATA_STORAGE,
    ENABLE_ANALYTICS,
    ENVIRONMENT,
    HLTV_URL,
    LOG_LEVEL,
    LOG_FILE
)

__all__ = [
    "DB_NAME",
    "DB_USER",
    "DB_PASS",
    "DB_HOST",
    "DB_PORT",
    "START_DATE",
    "END_DATE",
    "DEBUG_MODE",
    "MAX_MATCHES",
    "ENABLE_DEMO_DOWNLOADS",
    "ENABLE_DATA_STORAGE",
    "ENABLE_ANALYTICS",
    "ENVIRONMENT",
    "HLTV_URL",
    "LOG_LEVEL",
    "LOG_FILE"
]
