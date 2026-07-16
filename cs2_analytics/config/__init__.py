"""
Configuration module for CS2 Analytics.

This file ensures that configuration settings from `config.py` are easily accessible
throughout the project without needing direct imports.
"""

from .config import (
    API_CORS_ORIGINS,
    API_DEBUG,
    API_HOST,
    API_PORT,
    DB_HOST,
    DB_NAME,
    DB_PASS,
    DB_PORT,
    DB_USER,
    DEBUG_MODE,
    ENABLE_ANALYTICS,
    ENABLE_DATA_STORAGE,
    END_DATE,
    ENVIRONMENT,
    LOG_FILE,
    LOG_LEVEL,
    MAX_MATCHES,
    SOURCE_URL,
    START_DATE,
)

__all__ = [
    "API_CORS_ORIGINS",
    "API_DEBUG",
    "API_HOST",
    "API_PORT",
    "DEBUG_MODE",
    "DB_NAME",
    "DB_HOST",
    "DB_PASS",
    "DB_PORT",
    "DB_USER",
    "ENABLE_ANALYTICS",
    "ENABLE_DATA_STORAGE",
    "END_DATE",
    "ENVIRONMENT",
    "LOG_FILE",
    "LOG_LEVEL",
    "MAX_MATCHES",
    "SOURCE_URL",
    "START_DATE",
]
