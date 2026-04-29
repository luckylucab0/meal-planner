"""Router für `/api/settings` — App-Konfiguration (CalDAV + Feature-Flags).

Passwörter werden vor dem Persistieren mit Fernet verschlüsselt; das
Klartext-Passwort verlässt den Server **nie** wieder. Das Frontend zeigt
lediglich, ob ein Passwort gesetzt ist (`caldav_password_set`).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crypto
from app.crypto import EncryptionNotConfiguredError
from app.database import get_db
from app.models import AppSettings
from app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_ID = 1


def _get_or_create(db: Session) -> AppSettings:
    row = db.get(AppSettings, SETTINGS_ID)
    if row is None:
        row = AppSettings(id=SETTINGS_ID)
        db.add(row)
        db.flush()
    return row


def _to_read(row: AppSettings) -> SettingsRead:
    return SettingsRead(
        caldav_enabled=row.caldav_enabled,
        caldav_username=row.caldav_username,
        caldav_calendar_name=row.caldav_calendar_name,
        caldav_password_set=row.caldav_password_enc is not None,
    )


@router.get("", response_model=SettingsRead)
def get_settings_endpoint(db: Session = Depends(get_db)) -> SettingsRead:
    row = _get_or_create(db)
    db.commit()
    db.refresh(row)
    return _to_read(row)


@router.put("", response_model=SettingsRead)
def update_settings_endpoint(payload: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsRead:
    row = _get_or_create(db)
    row.caldav_enabled = payload.caldav_enabled
    row.caldav_username = payload.caldav_username
    row.caldav_calendar_name = payload.caldav_calendar_name

    if payload.caldav_password:  # leer/None → bestehenden Cipher beibehalten
        try:
            row.caldav_password_enc = crypto.encrypt(payload.caldav_password)
        except EncryptionNotConfiguredError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _to_read(row)
