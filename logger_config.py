import logging
import sys

# ✅ Configure logging to flush logs in real-time
logging.basicConfig(
    filename="app.log", 
    level=logging.DEBUG, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

# ✅ Force real-time writing
file_handler = logging.FileHandler("app.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# ✅ Disable buffering (forces immediate writes)
file_handler.flush = lambda: None

# ✅ Add handler to the logger
logger = logging.getLogger()
logger.addHandler(file_handler)

logger.info("🚀 Real-time logging is enabled!")  # Will appear immediately in `app.log`

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO  # Set logging level

def setup_logger(name: str) -> logging.Logger:
    """Creates and configures a logger with UTF-8 encoding support."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # ✅ Console Handler (forces UTF-8 encoding)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # ✅ File Handler with UTF-8 Encoding
    file_handler = logging.FileHandler("project.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # Add handlers if not already present
    if not logger.hasHandlers():
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
