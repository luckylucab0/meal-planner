"""Router für `/api/preferences` — GET und PUT auf die Singleton-Zeile (id=1).

Wenn die Zeile noch nicht existiert (frische Installation), wird sie beim
ersten GET mit Defaults aus `UserPreferences.default_payload()` angelegt
— so vermeidet der Server, dass das Frontend mit einem 404 starten muss.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserPreferences
from app.schemas.preferences import PreferencesRead, PreferencesUpdate

router = APIRouter(prefix="/api/preferences", tags=["preferences"])

PREFS_ID = 1


def _get_or_create_singleton(db: Session) -> UserPreferences:
    """Lädt id=1 oder legt ihn mit Defaults an. Commit erfolgt im Aufrufer."""
    row = db.get(UserPreferences, PREFS_ID)
    if row is None:
        row = UserPreferences(**UserPreferences.default_payload())
        db.add(row)
        db.flush()
    return row


def _to_read(row: UserPreferences) -> PreferencesRead:
    """Mappt das ORM-Objekt auf die Public-API-Form."""
    return PreferencesRead(
        whitelist=list(row.whitelist_json),
        blacklist=list(row.blacklist_json),
        fitness_goal=row.fitness_goal,  # type: ignore[arg-type]
        kcal_target=row.kcal_target,
        protein_target_g=row.protein_target_g,
        max_prep_min=row.max_prep_min,
        weekly_budget_chf=row.weekly_budget_chf,
        diet_tags=list(row.diet_tags_json),
        updated_at=row.updated_at,
    )


@router.get("", response_model=PreferencesRead)
def get_preferences(db: Session = Depends(get_db)) -> PreferencesRead:
    row = _get_or_create_singleton(db)
    db.commit()
    db.refresh(row)
    return _to_read(row)


@router.put("", response_model=PreferencesRead)
def update_preferences(
    payload: PreferencesUpdate, db: Session = Depends(get_db)
) -> PreferencesRead:
    row = _get_or_create_singleton(db)
    row.whitelist_json = payload.whitelist
    row.blacklist_json = payload.blacklist
    row.fitness_goal = payload.fitness_goal
    row.kcal_target = payload.kcal_target
    row.protein_target_g = payload.protein_target_g
    row.max_prep_min = payload.max_prep_min
    row.weekly_budget_chf = payload.weekly_budget_chf
    row.diet_tags_json = payload.diet_tags
    db.commit()
    db.refresh(row)
    return _to_read(row)
