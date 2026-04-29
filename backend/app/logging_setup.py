"""Loguru-Setup mit rotierenden Logfiles.

Konfiguriert:
- Ausgabe nach stdout (für `docker logs`).
- Rotierende Datei in `settings.log_dir/meal_planner.log` (10 MB pro Datei,
  max. 14 Tage Aufbewahrung, gzip-Kompression).

Idempotent: kann gefahrlos mehrfach aufgerufen werden (z.B. in Tests).
"""

from __future__ import annotations

import sys

from loguru import logger

from app.config import settings

_INITIALIZED = False


def setup_logging() -> None:
    """Initialisiert Loguru — Aufruf einmalig beim App-Start."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
            "<level>{level: <8}</level> "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )

    settings.log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        settings.log_dir / "meal_planner.log",
        level=settings.log_level,
        rotation="10 MB",
        retention="14 days",
        compression="gz",
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    _INITIALIZED = True
    logger.info("Logging initialisiert (level={})", settings.log_level)
