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
    BROWSER_HEADLESS,
    DB_HOST,
    DB_NAME,
    DB_PASS,
    DB_PORT,
    DB_USER,
    DEBUG_MODE,
    ENVIRONMENT,
    LOG_LEVEL,
    SOURCE_URL,
)

__all__ = [
    "API_CORS_ORIGINS",
    "API_DEBUG",
    "API_HOST",
    "API_PORT",
    "BROWSER_HEADLESS",
    "DEBUG_MODE",
    "DB_NAME",
    "DB_HOST",
    "DB_PASS",
    "DB_PORT",
    "DB_USER",
    "ENVIRONMENT",
    "LOG_LEVEL",
    "SOURCE_URL",
]
