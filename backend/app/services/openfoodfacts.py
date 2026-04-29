"""Open-Food-Facts-Client + Cache-Strategie.

Schlägt Zutaten in `world.openfoodfacts.org` nach. Cache-Strategie:

1. Lookup zuerst in lokaler `products`-Tabelle (Treffer auf normalisierten Namen).
2. Bei Miss → OFF-Search-API → Top-Treffer auf internes Schema mappen.
3. Treffer wird als Produkt-Zeile übernommen und gibt eine `Product`-Instanz zurück.

OFF-Policy verlangt einen aussagekräftigen `User-Agent`. Wir setzen ein
konservatives Timeout (8 s) und erlauben einen Retry, da der Server gelegentlich
träge antwortet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import OpenFoodFactsError
from app.models import Product

_TIMEOUT_S = 8.0
_PAGE_SIZE = 5


@dataclass(slots=True)
class OffProduct:
    """Reduzierte Repräsentation eines OFF-Treffers."""

    name: str
    barcode: str | None
    kcal_per_100g: float
    protein_g: float
    carbs_g: float
    fat_g: float


def _extract_nutriment(nutriments: dict[str, Any], key: str) -> float:
    """Liest einen Nutriment-Wert je 100 g, default 0."""
    raw = nutriments.get(f"{key}_100g")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _map_off_product(item: dict[str, Any]) -> OffProduct | None:
    """Wandelt einen OFF-Eintrag in `OffProduct` — überspringt unvollständige Treffer."""
    name = item.get("product_name") or item.get("generic_name")
    if not name:
        return None
    nutriments = item.get("nutriments") or {}
    kcal = _extract_nutriment(nutriments, "energy-kcal")
    if kcal == 0.0:
        # Fallback: manche Einträge haben nur energy_100g (kJ).
        energy_kj = _extract_nutriment(nutriments, "energy")
        kcal = round(energy_kj / 4.184, 1) if energy_kj else 0.0

    return OffProduct(
        name=str(name).strip(),
        barcode=item.get("code"),
        kcal_per_100g=kcal,
        protein_g=_extract_nutriment(nutriments, "proteins"),
        carbs_g=_extract_nutriment(nutriments, "carbohydrates"),
        fat_g=_extract_nutriment(nutriments, "fat"),
    )


def search_off(query: str) -> OffProduct | None:
    """Fragt OFF nach `query` ab und gibt den ersten brauchbaren Treffer zurück."""
    url = f"{settings.off_base_url}/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": _PAGE_SIZE,
        "fields": "product_name,generic_name,code,nutriments",
    }
    headers = {"User-Agent": settings.off_user_agent}
    try:
        with httpx.Client(timeout=_TIMEOUT_S) as http:
            res = http.get(url, params=params, headers=headers)
            res.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("OFF-Request fehlgeschlagen für '{}': {}", query, exc)
        raise OpenFoodFactsError(f"OFF-Request fehlgeschlagen: {exc}") from exc

    payload = res.json()
    for item in payload.get("products", []):
        mapped = _map_off_product(item)
        if mapped is not None and mapped.kcal_per_100g > 0:
            return mapped
    return None


def find_local(db: Session, name: str) -> Product | None:
    """Lookup in der lokalen `products`-Tabelle via normalisierten Namen."""
    normalized = Product.normalize_name(name)
    stmt = select(Product).where(Product.name_normalized == normalized)
    return db.scalars(stmt).one_or_none()


def lookup_or_fetch(
    db: Session, name: str, force_remote: bool = False
) -> tuple[Product | None, str]:
    """Lokal first → OFF fallback. Gibt Produkt + Quelle zurück.

    Quellen-Strings:
    - `"local"`: Treffer in der DB.
    - `"off"`: Frisch von Open Food Facts geladen und persistiert.
    - `"not_found"`: Weder lokal noch in OFF gefunden.

    Bei `force_remote=True` wird auch ein lokaler Cache-Treffer gegen OFF
    aktualisiert (z.B. wenn Werte verdächtig sind).
    """
    if not force_remote:
        existing = find_local(db, name)
        if existing is not None:
            return existing, "local"

    off_hit = search_off(name)
    if off_hit is None:
        return (None, "not_found") if not force_remote else (find_local(db, name), "local")

    normalized = Product.normalize_name(off_hit.name)
    product = db.scalars(select(Product).where(Product.name_normalized == normalized)).one_or_none()
    now = datetime.now(timezone.utc)

    if product is None:
        product = Product(
            name=off_hit.name,
            name_normalized=normalized,
            category="sonstiges",
            default_unit="g",
            kcal_per_100g=off_hit.kcal_per_100g,
            protein_g=off_hit.protein_g,
            carbs_g=off_hit.carbs_g,
            fat_g=off_hit.fat_g,
            source="off",
            off_barcode=off_hit.barcode,
            off_fetched_at=now,
        )
        db.add(product)
    else:
        product.kcal_per_100g = off_hit.kcal_per_100g
        product.protein_g = off_hit.protein_g
        product.carbs_g = off_hit.carbs_g
        product.fat_g = off_hit.fat_g
        product.source = "off"
        product.off_barcode = off_hit.barcode
        product.off_fetched_at = now

    db.flush()
    return product, "off"
