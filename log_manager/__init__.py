"""Logging module for configuring project-wide logging with error handling."""
try:
    from .logger_config import setup_logger
    __all__ = ["setup_logger"]
except ImportError as e:
    print(f"❌ Error importing logger_config: {e}")  # Fallback error message
    setup_logger = None  # Prevents crashes if logging fails