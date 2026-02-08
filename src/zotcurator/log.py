"""Logging configuration with verbosity levels."""

from __future__ import annotations

import logging
import sys

LOG_NAME = "zotc"

# Verbosity mapping:
# -q / 0 : CRITICAL+1 (silent)
# -v / 1 : WARNING
# (default) 2 : INFO
# -vvv / 3 : DEBUG
VERBOSITY_MAP: dict[int, int] = {
    0: logging.CRITICAL + 1,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}


def setup_logging(verbosity: int) -> logging.Logger:
    """Configure and return the application logger."""
    level = VERBOSITY_MAP.get(
        verbosity,
        logging.DEBUG if verbosity > 3 else logging.CRITICAL + 1,
    )
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        fmt = (
            "%(levelname)s [%(name)s] %(message)s"
            if level <= logging.DEBUG
            else "%(levelname)s: %(message)s"
        )
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    else:
        for handler in logger.handlers:
            handler.setLevel(level)
    return logger


def get_logger() -> logging.Logger:
    """Get the application logger."""
    return logging.getLogger(LOG_NAME)
