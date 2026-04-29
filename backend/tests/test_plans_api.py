"""End-to-End-Tests für `/api/plans` mit gemocktem Agent.

Wir patchen `_agent_factory`, damit kein echter Anthropic-Client gebaut wird.
Der Fake-Agent baut den Plan direkt in die DB (ähnlich wie `MealAgent`,
aber deterministisch).
"""

from __future__ import annotations

import datetime as dt
from datetime import date, datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import plans as plans_api
from app.models import (
    Meal,
    MealHistory,
    MealIngredient,
    MealPlan,
    Product,
    UserPreferences,
)


# ── Fake-Agent ─────────────────────────────────────────────────────────────


class _FakeAgent:
    """Simuliert `MealAgent.generate_plan()` ohne LLM-Roundtrip."""

    def __init__(self, db: Session, dishes: list[dict[str, Any]] | None = None) -> None:
        self.db = db
        self._dishes_by_slot = dishes or []
        self._next = 0

    def generate_plan(self, request: Any) -> int:
        plan = MealPlan(
            week_start=request.week_start,
            generated_at=datetime.now(timezone.utc),
            notes=request.notes,
            weekly_totals_json={},
        )
        self.db.add(plan)
        self.db.flush()

        total_kcal = 0.0
        total_protein = 0.0
        for meal_date, slot in request.slots:
            dish = self._dishes_by_slot[self._next % len(self._dishes_by_slot)]
            self._next += 1
            macros = dish["macros"]
            meal = Meal(
                plan_id=plan.id,
                date=meal_date,
                slot=slot,
                title=dish["title"],
                instructions=dish.get("instructions", ""),
                prep_time_min=dish.get("prep_time_min", 25),
                macros_json=macros,
            )
            self.db.add(meal)
            self.db.flush()
            for ing in dish["ingredients"]:
                self.db.add(
                    MealIngredient(meal_id=meal.id, product_id=ing["product_id"], grams=ing["grams"])
                )
            self.db.add(
                MealHistory(date=meal_date, slot=slot, title=dish["title"], plan_id=plan.id)
            )
            total_kcal += float(macros["kcal"])
            total_protein += float(macros["protein_g"])

        plan.weekly_totals_json = {
            "avg_kcal": round(total_kcal / max(len({d for d, _ in request.slots}), 1), 1),
            "avg_protein_g": round(total_protein / max(len({d for d, _ in request.slots}), 1), 1),
            "total_cost_chf": None,
        }
        self.db.commit()
        return plan.id


@pytest.fixture
def patch_agent(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Ersetzt `_agent_factory` mit einem konfigurierbaren Fake."""
    container: dict[str, Any] = {"dishes": []}

    def factory(db: Session) -> _FakeAgent:
        return _FakeAgent(db, container["dishes"])

    monkeypatch.setattr(plans_api, "_agent_factory", factory)
    return container


def _seed_products(client: TestClient) -> dict[str, int]:
    ids: dict[str, int] = {}
    for name, payload in [
        (
            "Quinoa",
            {
                "name": "Quinoa",
                "category": "getreide",
                "default_unit": "g",
                "kcal_per_100g": 360,
                "protein_g": 14,
                "carbs_g": 64,
                "fat_g": 6,
                "typical_pack_size_g": 500,
                "est_price_chf": 4.5,
            },
        ),
        (
            "Pouletbrust",
            {
                "name": "Pouletbrust",
                "category": "fleisch_fisch",
                "default_unit": "g",
                "kcal_per_100g": 110,
                "protein_g": 23,
                "carbs_g": 0,
                "fat_g": 1.5,
                "typical_pack_size_g": 300,
                "est_price_chf": 9.0,
            },
        ),
    ]:
        res = client.post("/api/products", json=payload)
        assert res.status_code == 201, res.text
        ids[name] = res.json()["id"]
    return ids


# ── Tests ──────────────────────────────────────────────────────────────────


def test_generate_persists_plan_and_returns_full_payload(
    client: TestClient, patch_agent: dict[str, Any]
) -> None:
    ids = _seed_products(client)
    patch_agent["dishes"] = [
        {
            "title": "Quinoa-Bowl",
            "instructions": "Quinoa kochen.",
            "prep_time_min": 25,
            "macros": {"kcal": 540.0, "protein_g": 32.0, "carbs_g": 70.0, "fat_g": 12.0, "incomplete": False},
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
                {"date": "2026-05-04", "slot": "dinner"},
            ],
            "notes": "Mo zu Hause",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["week_start"] == "2026-05-04"
    assert body["notes"] == "Mo zu Hause"
    assert len(body["meals"]) == 2
    titles = [m["title"] for m in body["meals"]]
    assert all(t == "Quinoa-Bowl" for t in titles)
    # Zutaten sind aufgelöst.
    first_meal = body["meals"][0]
    names = [i["name"] for i in first_meal["ingredients"]]
    assert "Quinoa" in names and "Pouletbrust" in names


def test_current_returns_latest(client: TestClient, patch_agent: dict[str, Any]) -> None:
    ids = _seed_products(client)
    patch_agent["dishes"] = [
        {
            "title": "Plan A",
            "macros": {"kcal": 500, "protein_g": 30, "carbs_g": 60, "fat_g": 10, "incomplete": False},
            "ingredients": [{"product_id": ids["Quinoa"], "grams": 80}],
        }
    ]
    client.post(
        "/api/plans/generate",
        json={"week_start": "2026-04-27", "slots": [{"date": "2026-04-27", "slot": "lunch"}]},
    )
    patch_agent["dishes"][0]["title"] = "Plan B"
    client.post(
        "/api/plans/generate",
        json={"week_start": "2026-05-04", "slots": [{"date": "2026-05-04", "slot": "lunch"}]},
    )

    res = client.get("/api/plans/current")
    assert res.status_code == 200
    body = res.json()
    assert body["week_start"] == "2026-05-04"
    assert body["meals"][0]["title"] == "Plan B"


def test_history_returns_summaries(client: TestClient, patch_agent: dict[str, Any]) -> None:
    ids = _seed_products(client)
    patch_agent["dishes"] = [
        {
            "title": "Test",
            "macros": {"kcal": 500, "protein_g": 30, "carbs_g": 60, "fat_g": 10, "incomplete": False},
            "ingredients": [{"product_id": ids["Quinoa"], "grams": 80}],
        }
    ]
    for week in ["2026-04-27", "2026-05-04", "2026-05-11"]:
        d = dt.date.fromisoformat(week)
        client.post(
            "/api/plans/generate",
            json={"week_start": week, "slots": [{"date": d.isoformat(), "slot": "lunch"}]},
        )

    res = client.get("/api/plans/history?limit=2")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    # Sortierung absteigend nach week_start.
    assert items[0]["week_start"] == "2026-05-11"
    assert items[1]["week_start"] == "2026-05-04"
    assert items[0]["meals_count"] == 1


def test_get_by_id_404_for_missing(client: TestClient) -> None:
    res = client.get("/api/plans/999")
    assert res.status_code == 404


def test_delete_plan(client: TestClient, patch_agent: dict[str, Any]) -> None:
    ids = _seed_products(client)
    patch_agent["dishes"] = [
        {
            "title": "X",
            "macros": {"kcal": 500, "protein_g": 30, "carbs_g": 60, "fat_g": 10, "incomplete": False},
            "ingredients": [{"product_id": ids["Quinoa"], "grams": 80}],
        }
    ]
    pid = client.post(
        "/api/plans/generate",
        json={"week_start": "2026-05-04", "slots": [{"date": "2026-05-04", "slot": "lunch"}]},
    ).json()["id"]
    res = client.delete(f"/api/plans/{pid}")
    assert res.status_code == 204
    assert client.get(f"/api/plans/{pid}").status_code == 404


def test_regenerate_replaces_meal_in_plan(
    client: TestClient, patch_agent: dict[str, Any]
) -> None:
    ids = _seed_products(client)
    patch_agent["dishes"] = [
        {
            "title": "Original",
            "instructions": "alt",
            "prep_time_min": 25,
            "macros": {"kcal": 500, "protein_g": 30, "carbs_g": 60, "fat_g": 10, "incomplete": False},
            "ingredients": [{"product_id": ids["Quinoa"], "grams": 80}],
        }
    ]
    plan = client.post(
        "/api/plans/generate",
        json={"week_start": "2026-05-04", "slots": [{"date": "2026-05-04", "slot": "lunch"}]},
    ).json()
    plan_id = plan["id"]
    meal_id = plan["meals"][0]["id"]

    patch_agent["dishes"] = [
        {
            "title": "Neu",
            "instructions": "neu",
            "prep_time_min": 18,
            "macros": {"kcal": 600, "protein_g": 35, "carbs_g": 50, "fat_g": 18, "incomplete": False},
            "ingredients": [{"product_id": ids["Pouletbrust"], "grams": 150}],
        }
    ]
    res = client.post(f"/api/plans/{plan_id}/meals/{meal_id}/regenerate")
    assert res.status_code == 200, res.text
    new_meal = res.json()
    assert new_meal["id"] == meal_id  # gleiche Mahlzeit-ID, neuer Inhalt
    assert new_meal["title"] == "Neu"
    assert new_meal["instructions"] == "neu"
    assert new_meal["prep_time_min"] == 18
    assert new_meal["ingredients"][0]["name"] == "Pouletbrust"

    # Mini-Plan, der zur Regenerierung gebraucht wurde, ist wieder weg.
    listing = client.get("/api/plans/history?limit=20").json()
    assert len(listing) == 1


def test_generate_returns_503_when_anthropic_key_missing(client: TestClient) -> None:
    """Ohne API-Key (und ohne Fake-Override) liefert das Endpoint 503."""
    # Wir lassen `_agent_factory` unverändert (also den echten Pfad).
    res = client.post(
        "/api/plans/generate",
        json={
            "week_start": "2026-05-04",
            "slots": [{"date": "2026-05-04", "slot": "lunch"}],
        },
    )
    assert res.status_code == 503
