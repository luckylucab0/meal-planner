"""Tests für `/api/shopping-list` und den zugrundeliegenden Aggregator."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import plans as plans_api
from tests.test_plans_api import _FakeAgent, _seed_products


@pytest.fixture
def patched_plan(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    ids = _seed_products(client)
    container: dict[str, Any] = {"dishes": []}

    def factory(db):
        return _FakeAgent(db, container["dishes"])

    monkeypatch.setattr(plans_api, "_agent_factory", factory)

    container["dishes"] = [
        {
            "title": "Mahlzeit A",
            "instructions": "—",
            "prep_time_min": 25,
            "macros": {"kcal": 500, "protein_g": 30, "carbs_g": 60, "fat_g": 10, "incomplete": False},
            "ingredients": [
                {"product_id": ids["Quinoa"], "grams": 80},
                {"product_id": ids["Pouletbrust"], "grams": 150},
            ],
        },
        {
            "title": "Mahlzeit B",
            "instructions": "—",
            "prep_time_min": 25,
            "macros": {"kcal": 600, "protein_g": 35, "carbs_g": 65, "fat_g": 12, "incomplete": False},
            "ingredients": [
                {"product_id": ids["Quinoa"], "grams": 100},
                {"product_id": ids["Pouletbrust"], "grams": 200},
            ],
        },
    ]
    res = client.post(
        "/api/plans/generate",
        json={
            "week_start": "2026-05-04",
            "slots": [
                {"date": "2026-05-04", "slot": "lunch"},
                {"date": "2026-05-04", "slot": "dinner"},
            ],
        },
    )
    return {"ids": ids, "plan_id": res.json()["id"]}


def test_shopping_list_aggregates_and_groups(client: TestClient, patched_plan: dict[str, Any]) -> None:
    plan_id = patched_plan["plan_id"]
    res = client.get(f"/api/shopping-list/{plan_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["plan_id"] == plan_id
    categories = [g["category"] for g in body["groups"]]
    # Schweizer Supermarkt-Layout: Fleisch/Fisch kommt vor Getreide/Trockenwaren.
    assert categories.index("fleisch_fisch") < categories.index("getreide")

    # Quinoa: 180 g gebraucht → 1 Pack à 500 g.
    quinoa_group = next(g for g in body["groups"] if g["category"] == "getreide")
    quinoa_item = next(i for i in quinoa_group["items"] if i["name"] == "Quinoa")
    assert quinoa_item["grams_needed"] == 180
    assert quinoa_item["grams_to_buy"] == 500
    assert quinoa_item["packs"] == 1

    # Pouletbrust: 350 g gebraucht → 2 Packs à 300 g = 600 g.
    fleisch_group = next(g for g in body["groups"] if g["category"] == "fleisch_fisch")
    poulet = next(i for i in fleisch_group["items"] if i["name"] == "Pouletbrust")
    assert poulet["grams_needed"] == 350
    assert poulet["packs"] == 2
    assert poulet["grams_to_buy"] == 600

    # Total cost = 1×4.50 + 2×9.00 = 22.50.
    assert float(body["total_cost_chf"]) == pytest.approx(22.50, abs=0.01)


def test_shopping_list_txt_download(client: TestClient, patched_plan: dict[str, Any]) -> None:
    res = client.get(f"/api/shopping-list/{patched_plan['plan_id']}.txt")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    text = res.text
    assert "Einkaufsliste — Woche ab 2026-05-04" in text
    assert "Quinoa" in text and "Pouletbrust" in text
    assert "Geschätzte Gesamtkosten" in text


def test_shopping_list_404_for_missing_plan(client: TestClient) -> None:
    res = client.get("/api/shopping-list/9999")
    assert res.status_code == 404
