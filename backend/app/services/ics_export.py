"""iCalendar-Export der Mahlzeiten eines Wochenplans (RFC 5545).

Erzeugt pro Mahlzeit ein VEVENT mit stabiler UID (idempotenter Re-Import
in jeden Kalender). Mittag startet 12:00, Abend 19:00 in der konfigurierten
Zeitzone (`settings.timezone`, default Europe/Zurich); Dauer 60 min.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, time, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from app.config import settings
from app.models import Meal, MealPlan

# Slot → Startzeit (lokale Zeit in der konfigurierten Zone).
_SLOT_TIMES: dict[str, time] = {
    "lunch": time(12, 0),
    "dinner": time(19, 0),
}
_DEFAULT_DURATION = timedelta(minutes=60)


def _start_for(meal_date: date_type, slot: str, tz: ZoneInfo) -> datetime:
    start = _SLOT_TIMES.get(slot, time(12, 0))
    return datetime.combine(meal_date, start, tzinfo=tz)


def _format_description(meal: Meal, ingredient_names: dict[int, str]) -> str:
    lines: list[str] = []
    if meal.ingredients:
        lines.append("Zutaten:")
        for ing in meal.ingredients:
            name = ingredient_names.get(ing.product_id, f"#{ing.product_id}")
            lines.append(f"  - {ing.grams:g} g {name}")
        lines.append("")
    macros = meal.macros_json or {}
    lines.append(
        f"Makros: {round(float(macros.get('kcal', 0)))} kcal, "
        f"{round(float(macros.get('protein_g', 0)))} g Protein, "
        f"{round(float(macros.get('carbs_g', 0)))} g Carbs, "
        f"{round(float(macros.get('fat_g', 0)))} g Fett"
    )
    if meal.prep_time_min:
        lines.append(f"Zubereitung: {meal.prep_time_min} min")
    if meal.instructions:
        lines.append("")
        lines.append(meal.instructions)
    return "\n".join(lines)


def build_calendar(plan: MealPlan, ingredient_names: dict[int, str]) -> bytes:
    """Erzeugt das iCalendar-Dokument als UTF-8-Bytes (zum Streamen geeignet)."""
    cal = Calendar()
    cal.add("prodid", "-//Meal Planner//selfhosted//DE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")

    tz = ZoneInfo(settings.timezone)
    for meal in plan.meals:
        ev = Event()
        ev.add("uid", f"meal-{plan.id}-{meal.id}@meal-planner.local")
        ev.add("summary", meal.title)
        ev.add("dtstart", _start_for(meal.date, meal.slot, tz))
        ev.add("dtend", _start_for(meal.date, meal.slot, tz) + _DEFAULT_DURATION)
        ev.add("dtstamp", datetime.now(tz))
        ev.add("description", _format_description(meal, ingredient_names))
        cal.add_component(ev)

    return cal.to_ical()


def collect_ingredient_names(meals: Iterable[Meal]) -> set[int]:
    """Sammelt Produkt-IDs, damit der Aufrufer einmalig auflösen kann."""
    return {ing.product_id for m in meals for ing in m.ingredients}
