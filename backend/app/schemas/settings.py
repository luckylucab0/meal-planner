"""Pydantic-Schemas für `/api/settings` (App-Konfiguration: CalDAV etc.)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SettingsRead(BaseModel):
    """Antwort-Form. Passwort wird **nie** zurückgegeben."""

    caldav_enabled: bool
    caldav_username: str | None
    caldav_calendar_name: str
    caldav_password_set: bool


class SettingsUpdate(BaseModel):
    """Update-Body — Felder sind optional, Passwort nur wenn gesetzt überschreiben.

    `caldav_password` als Klartext: wird serverseitig Fernet-verschlüsselt.
    Leerstring oder `None` → Passwort bleibt unverändert.
    """

    caldav_enabled: bool = False
    caldav_username: str | None = Field(default=None, max_length=200)
    caldav_calendar_name: str = Field(default="Meal Plan", max_length=100)
    caldav_password: str | None = Field(default=None, max_length=200)


class CalDavSyncResult(BaseModel):
    """Antwort von `POST /api/calendar/sync-apple/{plan_id}`."""

    created: int
    updated: int
    plan_id: int
    calendar_name: str
