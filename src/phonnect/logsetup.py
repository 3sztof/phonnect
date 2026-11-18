from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from phonnect import paths

LOGGER = "phonnect"
FORMAT = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")


def setup_logging(to_file: bool, to_console: bool) -> None:
    """Only the long-running process (run/tray) writes the log file, so there is a single writer."""
    logger = logging.getLogger(LOGGER)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    if to_file:
        path = paths.log_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Capped at ~2 MB total: the live file rotates at 1 MB, one old copy is kept.
        fh = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=1, encoding="utf-8")
        fh.setFormatter(FORMAT)
        logger.addHandler(fh)
    # pythonw has no stderr.
    if to_console and sys.stderr is not None:
        sh = logging.StreamHandler()
        sh.setFormatter(FORMAT)
        logger.addHandler(sh)
