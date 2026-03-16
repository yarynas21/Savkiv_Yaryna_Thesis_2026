"""
Logger Module
==============
Centralized logging configuration for the MAS system.

Usage:
    from utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Message")
    logger.error("Error occurred", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# ── Log directory ────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ── Log format ────────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── File handler format (more detailed) ───────────────────────────────────────
FILE_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure root logger with console and file handlers.

    Parameters
    ----------
    level       : logging level (default: INFO)
    log_to_file : whether to write logs to file (default: True)
    log_file    : custom log file path (default: logs/mas.log)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # ── Console handler ─────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # ── File handler ─────────────────────────────────────────────────────────
    if log_to_file:
        if log_file is None:
            log_file = LOG_DIR / "mas.log"
        else:
            log_file = Path(log_file)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # File gets all levels
        file_formatter = logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger instance for a module.

    Parameters
    ----------
    name  : module name (usually __name__)
    level : optional override level for this logger

    Returns
    -------
    Logger instance
    """
    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)

    # If no handlers exist, setup default logging
    if not logger.handlers and not logging.getLogger().handlers:
        setup_logging()

    return logger


# ── Initialize on import ──────────────────────────────────────────────────────
setup_logging()
