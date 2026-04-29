"""Tests für `/api/settings` und `/api/calendar/sync-apple/{id}`.

Encryption-Key wird pro Test via `monkeypatch` auf einen frisch generierten
Fernet-Key gesetzt, damit der Round-Trip funktioniert ohne `.env`.
"""

from __future__ import annotations

from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.api import plans as plans_api
from app.config import settings as app_settings
from app.services import caldav_sync
from tests.test_plans_api import _FakeAgent, _seed_products


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, "encryption_key", Fernet.generate_key().decode())


def test_settings_get_returns_defaults_for_fresh_db(client: TestClient) -> None:
    res = client.get("/api/settings")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "caldav_enabled": False,
        "caldav_username": None,
        "caldav_calendar_name": "Meal Plan",
        "caldav_password_set": False,
    }


def test_settings_put_encrypts_password_and_marks_set(client: TestClient) -> None:
    res = client.put(
        "/api/settings",
        json={
            "caldav_enabled": True,
            "caldav_username": "luca@example.test",
            "caldav_calendar_name": "Meal Plan",
            "caldav_password": "abcd-efgh-ijkl-mnop",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["caldav_enabled"] is True
    assert body["caldav_username"] == "luca@example.test"
    assert body["caldav_password_set"] is True
    # Klartext-Passwort darf nirgends im Response auftauchen.
    assert "abcd" not in res.text


def test_settings_put_without_password_keeps_existing_cipher(client: TestClient) -> None:
    client.put(
        "/api/settings",
        json={
            "caldav_enabled": True,
            "caldav_username": "u",
            "caldav_calendar_name": "Meal Plan",
            "caldav_password": "first-pwd",
        },
    )
    # Zweiter PUT ohne Passwort darf den alten Cipher nicht abschiessen.
    res = client.put(
        "/api/settings",
        json={
            "caldav_enabled": True,
            "caldav_username": "u",
            "caldav_calendar_name": "Speiseplan",
            "caldav_password": None,
        },
    )
    assert res.json()["caldav_password_set"] is True
    assert res.json()["caldav_calendar_name"] == "Speiseplan"


def _setup_plan(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> int:
    ids = _seed_products(client)
    container: dict[str, Any] = {"dishes": []}

    def factory(db):
        return _FakeAgent(db, container["dishes"])

    monkeypatch.setattr(plans_api, "_agent_factory", factory)
    container["dishes"] = [
        {
            "title": "X",
            "instructions": "—",
            "prep_time_min": 25,
            "macros": {"kcal": 500, "protein_g": 30, "carbs_g": 60, "fat_g": 10, "incomplete": False},
            "ingredients": [{"product_id": ids["Quinoa"], "grams": 80}],
        }
    ]
    return client.post(
        "/api/plans/generate",
        json={"week_start": "2026-05-04", "slots": [{"date": "2026-05-04", "slot": "lunch"}]},
    ).json()["id"]


def test_sync_returns_409_when_not_enabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_id = _setup_plan(client, monkeypatch)
    res = client.post(f"/api/calendar/sync-apple/{plan_id}")
    assert res.status_code == 409


def test_sync_passes_credentials_and_persists_events(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_id = _setup_plan(client, monkeypatch)
    client.put(
        "/api/settings",
        json={
            "caldav_enabled": True,
            "caldav_username": "luca@example.test",
            "caldav_calendar_name": "Meal Plan",
            "caldav_password": "secret-pwd",
        },
    )

    captured: dict[str, Any] = {"events": []}

    class FakeCalendar:
        name = "Meal Plan"

        def events(self):
            return []

        def save_event(self, ical: str) -> None:
            captured["events"].append(ical)

    class FakePrincipal:
        def calendars(self):
            return [FakeCalendar()]

        def make_calendar(self, name: str):
            raise AssertionError("Sollte nicht aufgerufen werden — Kalender existiert.")

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            captured["kwargs"] = kwargs

        def principal(self) -> FakePrincipal:
            return FakePrincipal()

    import caldav as caldav_mod

    monkeypatch.setattr(caldav_mod, "DAVClient", FakeClient)
    monkeypatch.setattr(caldav_sync, "caldav", caldav_mod)

    res = client.post(f"/api/calendar/sync-apple/{plan_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["created"] == 1
    assert body["updated"] == 0
    assert body["calendar_name"] == "Meal Plan"

    # Klartext-Passwort wurde an caldav übergeben (nicht der Cipher).
    assert captured["kwargs"]["password"] == "secret-pwd"
    assert captured["kwargs"]["username"] == "luca@example.test"
    # Ein VEVENT wurde gespeichert.
    assert any("BEGIN:VEVENT" in ev for ev in captured["events"])


def test_sync_returns_502_on_caldav_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_id = _setup_plan(client, monkeypatch)
    client.put(
        "/api/settings",
        json={
            "caldav_enabled": True,
            "caldav_username": "u",
            "caldav_calendar_name": "Meal Plan",
            "caldav_password": "pw",
        },
    )

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def principal(self):
            raise RuntimeError("Boom")

    import caldav as caldav_mod

    monkeypatch.setattr(caldav_mod, "DAVClient", FakeClient)
    res = client.post(f"/api/calendar/sync-apple/{plan_id}")
    assert res.status_code == 502
    assert "Boom" in res.text
