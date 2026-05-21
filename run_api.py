#!/usr/bin/env python
"""Run the FastAPI backend server."""

import uvicorn

from cs2_analytics.config import API_DEBUG, API_HOST, API_PORT
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Run the API server with environment-driven runtime settings."""
    logger.info(
        "Starting FastAPI server.",
        extra={"host": API_HOST, "port": API_PORT, "debug": API_DEBUG},
    )
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=API_DEBUG)


if __name__ == "__main__":
    main()
