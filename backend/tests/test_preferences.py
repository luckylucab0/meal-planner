"""End-to-End-Tests für `/api/preferences`."""

from fastapi.testclient import TestClient


def test_get_returns_defaults_on_fresh_db(client: TestClient) -> None:
    """Bei leerer DB legt der erste GET die Singleton-Zeile mit Defaults an."""
    res = client.get("/api/preferences")
    assert res.status_code == 200
    data = res.json()
    assert data["whitelist"] == []
    assert data["blacklist"] == []
    assert data["fitness_goal"] == "erhaltung"
    assert data["kcal_target"] == 2000
    assert data["protein_target_g"] == 120
    assert data["max_prep_min"] == 45
    assert data["weekly_budget_chf"] is None
    assert data["diet_tags"] == []


def test_put_persists_and_get_reads_back(client: TestClient) -> None:
    payload = {
        "whitelist": ["Quinoa", "Avocado"],
        "blacklist": ["Erdnüsse"],
        "fitness_goal": "muskelaufbau",
        "kcal_target": 2600,
        "protein_target_g": 180,
        "max_prep_min": 30,
        "weekly_budget_chf": 90.0,
        "diet_tags": ["vegetarisch"],
    }
    put = client.put("/api/preferences", json=payload)
    assert put.status_code == 200, put.text

    get = client.get("/api/preferences")
    assert get.status_code == 200
    data = get.json()
    assert data["whitelist"] == ["Quinoa", "Avocado"]
    assert data["blacklist"] == ["Erdnüsse"]
    assert data["fitness_goal"] == "muskelaufbau"
    assert data["kcal_target"] == 2600
    assert data["protein_target_g"] == 180
    assert data["max_prep_min"] == 30
    assert float(data["weekly_budget_chf"]) == 90.0
    assert data["diet_tags"] == ["vegetarisch"]


def test_put_validates_kcal_range(client: TestClient) -> None:
    bad = {
        "whitelist": [],
        "blacklist": [],
        "fitness_goal": "erhaltung",
        "kcal_target": 200,  # < 800 → 422
        "protein_target_g": 120,
        "max_prep_min": 45,
        "weekly_budget_chf": None,
        "diet_tags": [],
    }
    res = client.put("/api/preferences", json=bad)
    assert res.status_code == 422


def test_put_rejects_invalid_fitness_goal(client: TestClient) -> None:
    bad = {
        "whitelist": [],
        "blacklist": [],
        "fitness_goal": "bodybuilding",  # nicht in der Literal-Menge
        "kcal_target": 2000,
        "protein_target_g": 120,
        "max_prep_min": 45,
        "weekly_budget_chf": None,
        "diet_tags": [],
    }
    res = client.put("/api/preferences", json=bad)
    assert res.status_code == 422
