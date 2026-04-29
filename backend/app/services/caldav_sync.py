"""CalDAV-Sync mit Apple iCloud (App-spezifisches Passwort).

Liest verschlüsselte Credentials aus `app_settings`, verbindet sich mit
`https://caldav.icloud.com/`, sucht oder legt einen Kalender mit dem
konfigurierten Namen an und schreibt für jede Mahlzeit ein VEVENT.
UIDs sind dieselben wie beim ICS-Export (`meal-{plan_id}-{meal_id}@…`),
sodass Re-Sync bestehende Events aktualisiert statt neue zu erzeugen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import caldav
from caldav.lib.error import NotFoundError
from loguru import logger

from app import crypto
from app.exceptions import CalDavSyncError
from app.models import AppSettings, MealPlan, Product
from app.services import ics_export

ICLOUD_URL = "https://caldav.icloud.com/"


@dataclass(slots=True)
class SyncStats:
    created: int = 0
    updated: int = 0


def _credentials(settings_row: AppSettings) -> tuple[str, str]:
    if not settings_row.caldav_enabled:
        raise CalDavSyncError("CalDAV ist deaktiviert (settings.caldav_enabled=false).")
    if not settings_row.caldav_username or not settings_row.caldav_password_enc:
        raise CalDavSyncError("CalDAV-Username oder -Passwort fehlt.")
    try:
        password = crypto.decrypt(settings_row.caldav_password_enc)
    except Exception as exc:  # noqa: BLE001 — wir reichen kein Krypto-Detail nach aussen
        raise CalDavSyncError(f"Passwort konnte nicht entschlüsselt werden: {exc}") from exc
    return settings_row.caldav_username, password


def _get_or_create_calendar(client: caldav.DAVClient, name: str) -> Any:
    """Sucht einen Kalender mit `name` im Default-Principal, legt ihn sonst an."""
    principal = client.principal()
    for cal in principal.calendars():
        if cal.name == name:
            return cal
    return principal.make_calendar(name=name)


def _by_uid(calendar: Any) -> dict[str, Any]:
    """Map UID → event-object für Update-Detection."""
    out: dict[str, Any] = {}
    for ev in calendar.events():
        try:
            ical = ev.icalendar_instance
            for comp in ical.walk("VEVENT"):
                uid = str(comp.get("UID", "")).strip()
                if uid:
                    out[uid] = ev
        except Exception as exc:  # noqa: BLE001
            logger.debug("Konnte CalDAV-Event nicht parsen: {}", exc)
    return out


def sync_plan_to_icloud(
    settings_row: AppSettings,
    plan: MealPlan,
    products: dict[int, Product],
) -> SyncStats:
    """Synct alle Mahlzeiten eines Plans als VEVENTs in den iCloud-Kalender.

    Existiert ein Event mit derselben UID schon, wird es ersetzt; sonst neu
    angelegt. Schmeisst `CalDavSyncError` mit aussagekräftiger Meldung
    bei Konfig-/Auth-/Netz-Problemen.
    """
    username, password = _credentials(settings_row)
    logger.info(
        "CalDAV-Sync startet (user={}, calendar={})",
        username,
        settings_row.caldav_calendar_name,
    )

    try:
        client = caldav.DAVClient(url=ICLOUD_URL, username=username, password=password)
        calendar = _get_or_create_calendar(client, settings_row.caldav_calendar_name)
    except NotFoundError as exc:
        raise CalDavSyncError(f"CalDAV-Kalender nicht gefunden: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise CalDavSyncError(f"CalDAV-Verbindung fehlgeschlagen: {exc}") from exc

    existing = _by_uid(calendar)
    stats = SyncStats()
    names = {p.id: p.name for p in products.values()}

    # Wir verwenden den ICS-Builder pro Mahlzeit, indem wir einen Single-
    # Meal-Plan-Stub konstruieren, dann das einzelne VEVENT extrahieren.
    for meal in plan.meals:
        single_plan = MealPlan(id=plan.id, week_start=plan.week_start, generated_at=plan.generated_at)
        single_plan.meals = [meal]
        ical_bytes = ics_export.build_calendar(single_plan, names)
        ical_text = ical_bytes.decode("utf-8")

        uid = f"meal-{plan.id}-{meal.id}@meal-planner.local"
        try:
            if uid in existing:
                existing[uid].data = ical_text
                existing[uid].save()
                stats.updated += 1
            else:
                calendar.save_event(ical_text)
                stats.created += 1
        except Exception as exc:  # noqa: BLE001
            raise CalDavSyncError(
                f"Speichern des Events {uid} fehlgeschlagen: {exc}"
            ) from exc

    logger.info("CalDAV-Sync fertig (created={}, updated={})", stats.created, stats.updated)
    return stats


def get_caldav_client(url: str, username: str, password: str) -> caldav.DAVClient:
    """Wrapper, damit Tests die Funktion monkeypatchen können."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise CalDavSyncError(f"Ungültige CalDAV-URL: {url}")
    return caldav.DAVClient(url=url, username=username, password=password)
