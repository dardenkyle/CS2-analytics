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

    # ✅ Prevent duplicate handlers
    if logger.hasHandlers():
        return logger

    # ✅ Set log level from config
    log_level = logging.DEBUG  # Default: DEBUG for dev
    logger.setLevel(log_level)

    # ✅ Format logs
    log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    # ✅ File handler (write logs to file)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # ✅ Console handler (show logs in terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger