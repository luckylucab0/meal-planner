"""Tests für `services/openfoodfacts.py` mit gemockten OFF-Responses."""

from __future__ import annotations

import httpx
import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions import OpenFoodFactsError
from app.services import openfoodfacts


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)()


def _off_payload(*products):
    return {"products": list(products)}


def _product(name="Pouletbrust", code="9999", kcal=110, p=23.0, c=0.0, f=1.5):
    return {
        "product_name": name,
        "code": code,
        "nutriments": {
            "energy-kcal_100g": kcal,
            "proteins_100g": p,
            "carbohydrates_100g": c,
            "fat_100g": f,
        },
    }


@respx.mock
def test_search_off_returns_top_hit() -> None:
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(200, json=_off_payload(_product()))
    )
    hit = openfoodfacts.search_off("Pouletbrust")
    assert hit is not None
    assert hit.name == "Pouletbrust"
    assert hit.kcal_per_100g == 110
    assert hit.protein_g == 23.0


@respx.mock
def test_search_off_skips_entries_without_calories() -> None:
    bad = {"product_name": "Mystery", "nutriments": {}}
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(200, json=_off_payload(bad, _product(name="Quinoa")))
    )
    hit = openfoodfacts.search_off("Quinoa")
    assert hit is not None
    assert hit.name == "Quinoa"


@respx.mock
def test_search_off_returns_none_when_no_hits() -> None:
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(200, json=_off_payload())
    )
    assert openfoodfacts.search_off("Phantasialebensmittel") is None


@respx.mock
def test_search_off_raises_on_http_error() -> None:
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(503)
    )
    with pytest.raises(OpenFoodFactsError):
        openfoodfacts.search_off("Pouletbrust")


@respx.mock
def test_lookup_or_fetch_caches_remote_hit() -> None:
    db = _make_session()
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(200, json=_off_payload(_product(name="Quinoa", kcal=120, p=4.4)))
    )

    product, source = openfoodfacts.lookup_or_fetch(db, "Quinoa")
    db.commit()
    assert source == "off"
    assert product is not None
    assert product.source == "off"
    assert product.kcal_per_100g == 120
    assert product.off_fetched_at is not None

    # Zweiter Aufruf: lokaler Treffer, OFF wird nicht mehr gefragt.
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(500)  # Würde fehlschlagen, falls erneut aufgerufen.
    )
    product2, source2 = openfoodfacts.lookup_or_fetch(db, "QUINOA")  # case-insensitive
    assert source2 == "local"
    assert product2 is not None
    assert product2.id == product.id


@respx.mock
def test_lookup_or_fetch_returns_not_found_when_off_empty() -> None:
    db = _make_session()
    respx.get("https://world.openfoodfacts.org/cgi/search.pl").mock(
        return_value=httpx.Response(200, json=_off_payload())
    )
    product, source = openfoodfacts.lookup_or_fetch(db, "Phantasialebensmittel")
    assert product is None
    assert source == "not_found"
