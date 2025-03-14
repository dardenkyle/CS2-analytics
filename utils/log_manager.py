import logging
import os

# ✅ Define log directory & filename
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# ✅ Ensure the logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name):
    """
    Sets up and returns a logger with the specified name.
    Logs are written to logs/app.log and displayed in the console.
    """
    logger = logging.getLogger(name)

    # Prevent duplicate log handlers
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)  # ✅ Default: Log everything (DEBUG, INFO, WARNING, ERROR)

    # ✅ Format logs
    log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    # ✅ File handler (write logs to file)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    return logger
