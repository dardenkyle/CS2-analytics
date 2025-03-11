import logging
import os
from config import LOG_FILE, LOG_LEVEL

def setup_logger(name: str) -> logging.Logger:
    """
    Sets up and returns a logger with the specified name.

    Args:
        name (str): The name of the logger (typically `__name__`).

    Returns:
        logging.Logger: Configured logger instance.
    """

    # ✅ Create logs directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # ✅ Configure log format
    log_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # ✅ Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, "INFO"))  # Default to INFO if LOG_LEVEL is invalid

    # ✅ File handler (saves logs to a file)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # ✅ Console handler (prints logs to terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger
