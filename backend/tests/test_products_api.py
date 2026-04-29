"""End-to-End-Tests für `/api/products` (CRUD + Lookup mit OFF-Mock)."""

from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient


def _payload(name="Quinoa", category="getreide"):
    return {
        "name": name,
        "category": category,
        "default_unit": "g",
        "kcal_per_100g": 360,
        "protein_g": 14,
        "carbs_g": 64,
        "fat_g": 6,
        "typical_pack_size_g": 500,
        "est_price_chf": 4.5,
    }


def test_create_and_list(client: TestClient) -> None:
    res = client.post("/api/products", json=_payload())
    assert res.status_code == 201, res.text
    pid = res.json()["id"]

    listing = client.get("/api/products?q=Quin")
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    assert items[0]["id"] == pid
    assert items[0]["source"] == "manual"


def test_create_rejects_duplicate_name(client: TestClient) -> None:
    client.post("/api/products", json=_payload())
    res = client.post("/api/products", json=_payload(name="QUINOA"))  # case-insensitive Konflikt
    assert res.status_code == 409


def test_update_and_get(client: TestClient) -> None:
    pid = client.post("/api/products", json=_payload()).json()["id"]
    upd = _payload()
    upd["kcal_per_100g"] = 380
    upd["category"] = "trockenwaren"
    res = client.put(f"/api/products/{pid}", json=upd)
    assert res.status_code == 200
    assert res.json()["kcal_per_100g"] == 380
    assert res.json()["category"] == "trockenwaren"


def test_delete_unused_product(client: TestClient) -> None:
    pid = client.post("/api/products", json=_payload()).json()["id"]
    res = client.delete(f"/api/products/{pid}")
    assert res.status_code == 204
    follow = client.get(f"/api/products/{pid}")
    assert follow.status_code == 404


@respx.mock
def test_lookup_uses_local_first(client: TestClient) -> None:
    pid = client.post("/api/products", json=_payload(name="Lokale Linsen")).json()["id"]
    res = client.post("/api/products/lookup", json={"name": "lokale linsen"})
    assert res.status_code == 200
    body = res.json()
    assert body["source_resolved"] == "local"
    assert body["product"]["id"] == pid


@respx.mock
def test_lookup_falls_back_to_off_and_caches(client: TestClient) -> None:
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(
            200,
            json={
                "products": [
                    {
                        "product_name": "Haferflocken",
                        "code": "1234",
                        "nutriments": {
                            "energy-kcal_100g": 370,
                            "proteins_100g": 13,
                            "carbohydrates_100g": 60,
                            "fat_100g": 7,
                        },
                    }
                ]
            },
        )
    )
    res = client.post("/api/products/lookup", json={"name": "Haferflocken"})
    assert res.status_code == 200
    body = res.json()
    assert body["source_resolved"] == "off"
    assert body["product"]["source"] == "off"
    assert body["product"]["off_barcode"] == "1234"

    # Zweiter Lookup → lokal.
    res2 = client.post("/api/products/lookup", json={"name": "haferflocken"})
    assert res2.status_code == 200
    assert res2.json()["source_resolved"] == "local"


@respx.mock
def test_lookup_returns_not_found_when_off_empty(client: TestClient) -> None:
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(200, json={"products": []})
    )
    res = client.post("/api/products/lookup", json={"name": "Phantasielebensmittel"})
    assert res.status_code == 200
    assert res.json()["source_resolved"] == "not_found"
    assert res.json()["product"] is None
