"""This file sets up the logging configuration for the application."""

import logging
import os
from config.config import LOG_LEVEL

# Ensure the "logs" directory exists
LOG_DIR = "./logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "app.log")


def get_logger(name):
    """
    Sets up and returns a logger with the specified name.
    Logs are written to logs/app.log and displayed in the console.
    """
    logger = logging.getLogger(name)

    # ✅ Set log level from config
    logger.setLevel(LOG_LEVEL)

    # ✅ Format logs
    log_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # ✅ File handler (write logs to file)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # ✅ Console handler (show logs in terminal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger
