"""Tests für `/api/stats/macros`."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

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
            "title": "X",
            "instructions": "—",
            "prep_time_min": 25,
            "macros": {"kcal": 600, "protein_g": 40, "carbs_g": 70, "fat_g": 12, "incomplete": False},
            "ingredients": [{"product_id": ids["Quinoa"], "grams": 100}],
        }
    ]
    client.post(
        "/api/plans/generate",
        json={
            "week_start": "2026-04-27",
            "slots": [
                {"date": "2026-04-27", "slot": "lunch"},
                {"date": "2026-04-27", "slot": "dinner"},
                {"date": "2026-04-28", "slot": "lunch"},
            ],
        },
    )
    return {"ids": ids}


def test_macros_default_window_returns_seven_days(client: TestClient, patched: dict[str, Any]) -> None:
    res = client.get("/api/stats/macros?from=2026-04-27&to=2026-04-28")
    assert res.status_code == 200
    body = res.json()
    assert body["from"] == "2026-04-27"
    assert body["to"] == "2026-04-28"
    assert len(body["days"]) == 2

    day1 = body["days"][0]
    # Mo: 2 Mahlzeiten à 600 kcal = 1200, 80 g Protein.
    assert day1["date"] == "2026-04-27"
    assert day1["kcal"] == pytest.approx(1200.0, abs=0.1)
    assert day1["protein_g"] == pytest.approx(80.0, abs=0.1)
    assert day1["meals_count"] == 2

    day2 = body["days"][1]
    assert day2["date"] == "2026-04-28"
    assert day2["meals_count"] == 1
    assert day2["kcal"] == pytest.approx(600.0, abs=0.1)


def test_macros_includes_zero_days_for_gaps(client: TestClient, patched: dict[str, Any]) -> None:
    res = client.get("/api/stats/macros?from=2026-04-26&to=2026-04-29")
    body = res.json()
    assert len(body["days"]) == 4
    assert body["days"][0]["meals_count"] == 0  # 26.04 — kein Plan
    assert body["days"][3]["meals_count"] == 0  # 29.04 — kein Plan
