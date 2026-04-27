"""Centralized logging configuration for the MAS system."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
FILE_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"


def setup_logging(
    level: int = logging.INFO,
    log_to_file: Optional[bool] = None,
    log_file: Optional[str] = None,
) -> None:
    """Configure root logger with console and optional file handlers."""
    if log_to_file is None:
        log_to_file = os.getenv("LOG_TO_FILE", "false").lower() in {"1", "true", "yes", "on"}

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(console_handler)

    if log_to_file:
        if log_file is None:
            log_dir = Path(__file__).parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "mas.log"
        else:
            log_file = Path(log_file)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT))
        root_logger.addHandler(file_handler)

    root_logger.propagate = False


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Return a logger for the given module name."""
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    if not logger.handlers and not logging.getLogger().handlers:
        setup_logging()
    return logger


setup_logging()
