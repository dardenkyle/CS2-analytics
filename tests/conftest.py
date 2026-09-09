"""Pytest bootstrap: pin the test environment before any project code loads.

Every test run, local or CI, targets the disposable local database and
never the deployment one. This module loads `.env.test` into the process
environment with override on, so it beats both the application `.env`
(read later by the config module, which never overrides variables that are
already set) and any stray shell export. It then refuses to start unless
the resulting DB_HOST is a local database host. pytest imports the root
conftest before collecting any test module, so this runs before the config
module can be imported anywhere; the guard at the top makes that
assumption explicit rather than silent.

DB-backed tests take the `test_database` fixture, which connects to that
local database or skips when it is not running. See README, Run Tests.
"""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# tests.support imports only cs2_analytics.exceptions, which never touches
# config, so importing it here cannot pre-empt the environment pin below.
from tests.support import LOCAL_DB_HOSTS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_ENV_FILE = PROJECT_ROOT / ".env.test"
CONFIG_MODULE = "cs2_analytics.config.config"


def _pin_test_environment() -> None:
    """Load .env.test with override and refuse any non-local database host."""
    if CONFIG_MODULE in sys.modules:
        raise RuntimeError(
            f"{CONFIG_MODULE} was imported before tests/conftest.py loaded "
            f"{TEST_ENV_FILE.name}; the test environment cannot be guaranteed."
        )
    if not TEST_ENV_FILE.is_file():
        raise RuntimeError(f"{TEST_ENV_FILE} is missing; tests refuse to run without it.")
    load_dotenv(TEST_ENV_FILE, override=True)
    host = os.environ.get("DB_HOST", "")
    if host not in LOCAL_DB_HOSTS:
        raise RuntimeError(
            f"DB_HOST={host!r} after loading {TEST_ENV_FILE.name} is not one of "
            f"{LOCAL_DB_HOSTS}; refusing to run tests against a non-local database."
        )


_pin_test_environment()


@pytest.fixture(scope="session")
def test_database():
    """Shared connection to the local test database; skips when it is down."""
    from tests.support import NO_TEST_DB_REASON, open_test_database

    database = open_test_database()
    if database is None:
        pytest.skip(NO_TEST_DB_REASON)
    yield database
    database.close_db_pool()
