"""Centralized application logging for production-safe diagnostics."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_NAME = "sales_analyzer"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(LOG_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_path = Path(__file__).resolve().parent / "app_runtime.log"
    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_exception(context: str, exc: Exception) -> None:
    logger = get_logger()
    logger.exception("%s: %s", context, str(exc))
