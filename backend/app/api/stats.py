"""Router für `/api/stats/macros` — aggregierte Makros über Zeiträume."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Meal, UserPreferences
from app.schemas.stats import DailyMacros, MacrosRange

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/macros", response_model=MacrosRange)
def get_macros(
    db: Session = Depends(get_db),
    from_: date_type | None = Query(default=None, alias="from"),
    to: date_type | None = None,
) -> MacrosRange:
    """Aggregiert die Makros pro Tag im (inklusiven) Zeitraum.

    Default-Range: letzte 7 Tage bis heute. Tage ohne Mahlzeiten werden
    mit Nullwerten zurückgegeben, damit das Frontend ohne Lücken-Logik
    arbeiten kann.
    """
    today = date_type.today()
    end = to or today
    start = from_ or (end - timedelta(days=6))

    rows = db.scalars(
        select(Meal).where(Meal.date >= start, Meal.date <= end)
    ).all()

    by_day: dict[date_type, list[Meal]] = defaultdict(list)
    for meal in rows:
        by_day[meal.date].append(meal)

    days: list[DailyMacros] = []
    cursor = start
    while cursor <= end:
        meals = by_day.get(cursor, [])
        kcal = protein = carbs = fat = 0.0
        for m in meals:
            macros = m.macros_json or {}
            kcal += float(macros.get("kcal", 0))
            protein += float(macros.get("protein_g", 0))
            carbs += float(macros.get("carbs_g", 0))
            fat += float(macros.get("fat_g", 0))
        days.append(
            DailyMacros(
                date=cursor,
                kcal=round(kcal, 1),
                protein_g=round(protein, 1),
                carbs_g=round(carbs, 1),
                fat_g=round(fat, 1),
                meals_count=len(meals),
            )
        )
        cursor = cursor + timedelta(days=1)

    prefs = db.get(UserPreferences, 1)
    return MacrosRange(
        from_date=start,
        to=end,
        kcal_target=prefs.kcal_target if prefs else 2000,
        protein_target_g=prefs.protein_target_g if prefs else 120,
        days=days,
    )
