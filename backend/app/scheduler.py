"""APScheduler-Konfiguration.

Ein Sonntag-20:00-Job (in `settings.timezone`) setzt `last_reminder_at`
in `app_settings` — das Frontend rendert daraufhin einen Banner
„Neuen Wochenplan erstellen". Mehr macht der Scheduler bewusst nicht;
die eigentliche Plan-Generierung bleibt manuell, weil die Anwesenheit
pro Woche variiert.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config import settings
from app.database import SessionLocal
from app.models import AppSettings


def _set_reminder_flag() -> None:
    """Wird Sonntag 20:00 ausgeführt — markiert die App als „erinnerungsbereit"."""
    db = SessionLocal()
    try:
        row = db.get(AppSettings, 1)
        if row is None:
            row = AppSettings(id=1)
            db.add(row)
        row.last_reminder_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Wochenplan-Reminder gesetzt (Sonntag 20:00).")
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("Reminder-Job fehlgeschlagen: {}", exc)
    finally:
        db.close()


def make_scheduler() -> BackgroundScheduler:
    """Erstellt den globalen BackgroundScheduler — wird vom Lifespan gestartet."""
    tz = ZoneInfo(settings.timezone)
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        _set_reminder_flag,
        trigger=CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=tz),
        id="weekly-plan-reminder",
        replace_existing=True,
    )
    return scheduler
