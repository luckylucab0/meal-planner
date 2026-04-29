"""Makro-Aggregation auf Basis der Produkt-DB.

Wird vom Tool `calculate_nutrition` und vom Stats-Endpoint geteilt. Skaliert
linear auf die tatsächliche Menge in Gramm. Fehlt ein Produkt in der DB,
wird `incomplete=True` markiert — das Frontend kann dann einen Hinweis
zeigen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Product


@dataclass(slots=True)
class IngredientRef:
    """Verweis aus dem Plan: Produkt-ID + Gramm-Menge."""

    product_id: int
    grams: float


@dataclass(slots=True)
class Macros:
    """Aggregations-Resultat pro Mahlzeit oder Tag."""

    kcal: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    incomplete: bool = False

    def to_dict(self) -> dict[str, float | bool]:
        return {
            "kcal": round(self.kcal, 1),
            "protein_g": round(self.protein_g, 1),
            "carbs_g": round(self.carbs_g, 1),
            "fat_g": round(self.fat_g, 1),
            "incomplete": self.incomplete,
        }


def calculate_macros(db: Session, ingredients: Iterable[IngredientRef]) -> Macros:
    """Summiert die Makros über eine Zutatenliste."""
    total = Macros()
    for ref in ingredients:
        product = db.get(Product, ref.product_id)
        if product is None:
            total.incomplete = True
            continue
        scale = ref.grams / 100.0
        total.kcal += product.kcal_per_100g * scale
        total.protein_g += product.protein_g * scale
        total.carbs_g += product.carbs_g * scale
        total.fat_g += product.fat_g * scale
    return total
