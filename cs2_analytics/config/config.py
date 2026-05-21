"""Environment-backed runtime configuration for CS2 Analytics."""

import datetime as dt
import logging
import os

from dotenv import load_dotenv

from cs2_analytics.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

load_dotenv()

TRUTHY_VALUES = {"1", "true", "yes", "y", "on"}
FALSY_VALUES = {"0", "false", "no", "n", "off"}

PRODUCTION_REQUIRED_ENV_VARS = (
    "DB_NAME",
    "DB_USER",
    "DB_PASS",
    "DB_HOST",
    "DB_PORT",
    "API_HOST",
    "API_PORT",
    "API_CORS_ORIGINS",
    "DEBUG_MODE",
)


def _read_bool(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in TRUTHY_VALUES:
        return True
    if normalized in FALSY_VALUES:
        return False

    raise ConfigurationError(
        f"{name} must be one of: {', '.join(sorted(TRUTHY_VALUES | FALSY_VALUES))}."
    )


def _read_int(name: str, *, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc


def _read_csv(name: str, *, default: list[str]) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    values = [value.strip() for value in raw_value.split(",") if value.strip()]
    if not values:
        raise ConfigurationError(f"{name} must include at least one value.")
    return values


def _validate_production_environment(
    *,
    environment: str,
    debug_mode: bool,
    cors_origins: list[str],
) -> None:
    if environment != "production":
        return

    missing_vars = [
        name
        for name in PRODUCTION_REQUIRED_ENV_VARS
        if os.getenv(name) is None or os.getenv(name, "").strip() == ""
    ]
    if missing_vars:
        raise ConfigurationError(
            "Production configuration is missing required environment variables: "
            + ", ".join(missing_vars)
        )

    if debug_mode:
        raise ConfigurationError("DEBUG_MODE must be false in production.")

    if "*" in cors_origins:
        raise ConfigurationError("API_CORS_ORIGINS cannot include '*' in production.")


ENVIRONMENT = os.getenv("ENVIRONMENT", default="development").strip().lower()
DEBUG_MODE = _read_bool("DEBUG_MODE", default=True)

# Database Configuration
DB_NAME = os.getenv("DB_NAME", default="cs2_db")
DB_USER = os.getenv("DB_USER", default="postgres")
DB_PASS = os.getenv("DB_PASS", default="password")
DB_HOST = os.getenv("DB_HOST", default="localhost")
DB_PORT = os.getenv("DB_PORT", default="5432")
BATCH_SIZE = 1000

# API Configuration
API_HOST = os.getenv("API_HOST", default="127.0.0.1")
API_PORT = _read_int("API_PORT", default=8000)
API_DEBUG = DEBUG_MODE
API_CORS_ORIGINS = _read_csv(
    "API_CORS_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
)

# Feature Toggles
ENABLE_DATA_STORAGE = True
ENABLE_DEMO_DOWNLOADS = False
ENABLE_ANALYTICS = False

# Scraping Config
HLTV_URL = "https://www.hltv.org/results"
START_DATE = "2025-10-01"
END_DATE = str(dt.datetime.today().date())
MAX_MATCHES = 10

# Logging Config
LOG_LEVEL = logging.INFO
if DEBUG_MODE:
    LOG_LEVEL = logging.DEBUG
LOG_FILE = os.path.join(os.getcwd(), "logs", "app.log")

_validate_production_environment(
    environment=ENVIRONMENT,
    debug_mode=DEBUG_MODE,
    cors_origins=API_CORS_ORIGINS,
)
