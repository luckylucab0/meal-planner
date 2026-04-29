"""Tests für `/api/calendar/{plan_id}.ics`."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from icalendar import Calendar

from app.api import plans as plans_api
from tests.test_plans_api import _FakeAgent, _seed_products


@pytest.fixture
def patched(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    ids = _seed_products(client)
    container: dict[str, Any] = {"dishes": []}

    def factory(db):
        return _FakeAgent(db, container["dishes"])

    monkeypatch.setattr(plans_api, "_agent_factory", factory)
    container["dishes"] = [
        {
            "title": "Quinoa-Bowl",
            "instructions": "1. Quinoa kochen.\n2. Anrichten.",
            "prep_time_min": 25,
            "macros": {"kcal": 540, "protein_g": 32, "carbs_g": 70, "fat_g": 12, "incomplete": False},
            "ingredients": [
                {"product_id": ids["Quinoa"], "grams": 80},
                {"product_id": ids["Pouletbrust"], "grams": 150},
            ],
        }
    ]
    res = client.post(
        "/api/plans/generate",
        json={
            "week_start": "2026-05-04",
            "slots": [
                {"date": "2026-05-04", "slot": "lunch"},
                {"date": "2026-05-05", "slot": "dinner"},
            ],
        },
    )
    return {"plan_id": res.json()["id"]}


def test_ics_contains_event_per_meal(client: TestClient, patched: dict[str, Any]) -> None:
    res = client.get(f"/api/calendar/{patched['plan_id']}.ics")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/calendar")
    assert ".ics" in res.headers["content-disposition"]

    cal = Calendar.from_ical(res.content)
    events = [c for c in cal.walk("VEVENT")]
    assert len(events) == 2

    # Lunch ist 12:00 lokal, Dinner 19:00 lokal.
    summaries = sorted(str(e["SUMMARY"]) for e in events)
    assert summaries == ["Quinoa-Bowl", "Quinoa-Bowl"]
    starts = sorted(str(e["DTSTART"].dt) for e in events)
    assert "12:00" in starts[0]
    assert "19:00" in starts[1]

    # Beschreibung enthält Zutaten und Anleitung.
    desc_first = str(events[0]["DESCRIPTION"])
    assert "Quinoa" in desc_first
    assert "Pouletbrust" in desc_first
    assert "Makros" in desc_first


def test_ics_404_for_unknown_plan(client: TestClient) -> None:
    res = client.get("/api/calendar/9999.ics")
    assert res.status_code == 404
