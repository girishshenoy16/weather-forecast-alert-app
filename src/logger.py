"""Centralized Logging Architecture for Weather Forecast & Alert Application.

Provides structured, thread-safe, and dual-destination (File + Console) logging
with parameterized destinations to support isolated unit testing and operational auditing.
Logs are persisted to the logs/ directory (default: logs/weather_app.log).
"""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sys
from typing import Optional, Union

DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "weather_app.log"
DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] [%(name)s] - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str = "weather_app",
    log_file: Optional[Union[str, Path]] = DEFAULT_LOG_FILE,
    level: int = logging.INFO,
    console: bool = False,
    propagate: bool = False,
) -> logging.Logger:
    """Initialize and configure a dedicated application logger.

    Args:
        name: Hierarchical logger name (e.g. 'weather_app', 'weather_app.api_client').
        log_file: Target log file destination path. Set to None to disable file output.
        level: Minimum logging threshold (e.g. logging.DEBUG, logging.INFO).
        console: If True, attaches a StreamHandler sending log records to stdout.
        propagate: Whether log records propagate to the root logger (default: False).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    # Resolve normalized target path string if file logging requested
    target_path_str = str(Path(log_file).resolve()) if log_file else None

    # Check existing handlers to prevent duplicate handler accumulation
    has_file_handler_for_target = False
    has_console_handler = False

    for handler in list(logger.handlers):
        if isinstance(handler, logging.FileHandler):
            handler_path = str(Path(handler.baseFilename).resolve())
            if handler_path == target_path_str:
                has_file_handler_for_target = True
            else:
                # Remove stale file handler pointing elsewhere
                logger.removeHandler(handler)
                handler.close()
        elif isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            if console:
                has_console_handler = True
            else:
                logger.removeHandler(handler)
                handler.close()

    # Attach FileHandler if requested and not already attached
    if log_file and not has_file_handler_for_target:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Attach Console StreamHandler if requested and not already attached
    if console and not has_console_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "weather_app") -> logging.Logger:
    """Retrieve an existing logger or create one with default settings."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name=name)
    return logger
