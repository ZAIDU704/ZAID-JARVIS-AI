"""
logger.py
Central logging configuration for JARVIS AI.

Provides a rotating file handler plus console output so both developers
and end users can inspect what the assistant is doing.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

_CONFIGURED = False


def setup_logging(
    level: str = "INFO",
    log_file: str = "jarvis.log",
    max_bytes: int = 1_048_576,
    backup_count: int = 3,
) -> logging.Logger:
    """Configure and return the root 'jarvis' logger.

    Safe to call multiple times; only configures handlers once.
    """
    global _CONFIGURED
    logger = logging.getLogger("jarvis")

    if _CONFIGURED:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # If we can't write a log file (e.g. read-only filesystem), continue
        # with console-only logging rather than crashing the assistant.
        pass

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    _CONFIGURED = True
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'jarvis' namespace."""
    return logging.getLogger(f"jarvis.{name}")
