"""Aggregiert Plan-Zutaten zu einer Einkaufsliste, gerundet auf realistische Verkaufseinheiten.

Reihenfolge der Kategorien folgt dem typischen Schweizer Supermarkt-Layout
(grob Migros/Coop): Gemüse → Früchte → Brot → Milchprodukte → Fleisch/Fisch
→ Eier → Trockenwaren/Getreide → Tiefkühl → Öle/Gewürze → Sonstiges. Unbekannte
Kategorien landen unten unter „Sonstiges".
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Meal, MealPlan, Product

CATEGORY_ORDER: list[str] = [
    "gemuese",
    "fruechte",
    "brot",
    "milchprodukte",
    "fleisch_fisch",
    "eier",
    "getreide",
    "trockenwaren",
    "tiefkuehl",
    "oele_gewuerze",
    "sonstiges",
]

CATEGORY_LABELS: dict[str, str] = {
    "gemuese": "Gemüse",
    "fruechte": "Früchte",
    "brot": "Brot",
    "milchprodukte": "Milchprodukte",
    "fleisch_fisch": "Fleisch & Fisch",
    "eier": "Eier",
    "getreide": "Getreide",
    "trockenwaren": "Trockenwaren",
    "tiefkuehl": "Tiefkühl",
    "oele_gewuerze": "Öle & Gewürze",
    "sonstiges": "Sonstiges",
}


@dataclass(slots=True)
class ShoppingItem:
    product_id: int
    name: str
    category: str
    grams_needed: float
    grams_to_buy: float
    packs: int | None
    pack_size_g: float | None
    est_cost_chf: Decimal | None


@dataclass(slots=True)
class ShoppingGroup:
    category: str
    label: str
    items: list[ShoppingItem]


@dataclass(slots=True)
class ShoppingList:
    plan_id: int
    week_start: str
    groups: list[ShoppingGroup]
    total_cost_chf: Decimal | None


def _round_up_to_packs(grams_needed: float, pack_size: float | None) -> tuple[float, int | None]:
    """Rundet auf ganze Packungen, wenn `pack_size` bekannt — sonst auf 50 g."""
    if pack_size is None or pack_size <= 0:
        return (math.ceil(grams_needed / 50) * 50, None)
    packs = max(1, math.ceil(grams_needed / pack_size))
    return (packs * pack_size, packs)


def _category_index(cat: str) -> int:
    try:
        return CATEGORY_ORDER.index(cat)
    except ValueError:
        return CATEGORY_ORDER.index("sonstiges")


def build_shopping_list(db: Session, plan: MealPlan) -> ShoppingList:
    """Aggregiert die Mahlzeiten eines Plans zu einer Liste pro Produkt."""
    grams_by_product: dict[int, float] = defaultdict(float)
    for meal in plan.meals:
        for ing in meal.ingredients:
            grams_by_product[ing.product_id] += ing.grams

    items: list[ShoppingItem] = []
    total_cost = Decimal("0")
    has_cost = False
    for pid, grams_needed in grams_by_product.items():
        product = db.get(Product, pid)
        if product is None:
            continue
        grams_to_buy, packs = _round_up_to_packs(grams_needed, product.typical_pack_size_g)
        cost: Decimal | None = None
        if product.est_price_chf is not None:
            unit = float(product.typical_pack_size_g) if product.typical_pack_size_g else 100.0
            units_to_buy = grams_to_buy / unit
            cost = (Decimal(str(units_to_buy)) * Decimal(str(product.est_price_chf))).quantize(
                Decimal("0.01")
            )
            total_cost += cost
            has_cost = True
        items.append(
            ShoppingItem(
                product_id=pid,
                name=product.name,
                category=product.category,
                grams_needed=round(grams_needed, 1),
                grams_to_buy=round(grams_to_buy, 1),
                packs=packs,
                pack_size_g=float(product.typical_pack_size_g) if product.typical_pack_size_g else None,
                est_cost_chf=cost,
            )
        )

    items.sort(key=lambda it: (_category_index(it.category), it.name.lower()))

    groups_dict: dict[str, list[ShoppingItem]] = defaultdict(list)
    for it in items:
        cat = it.category if it.category in CATEGORY_LABELS else "sonstiges"
        groups_dict[cat].append(it)

    groups = [
        ShoppingGroup(category=cat, label=CATEGORY_LABELS[cat], items=groups_dict[cat])
        for cat in CATEGORY_ORDER
        if cat in groups_dict
    ]

    return ShoppingList(
        plan_id=plan.id,
        week_start=plan.week_start.isoformat(),
        groups=groups,
        total_cost_chf=total_cost.quantize(Decimal("0.01")) if has_cost else None,
    )


def render_txt(shopping: ShoppingList) -> str:
    """Druckbare Plain-Text-Variante (UTF-8)."""
    lines: list[str] = []
    lines.append(f"Einkaufsliste — Woche ab {shopping.week_start}")
    lines.append("=" * 50)
    for group in shopping.groups:
        lines.append("")
        lines.append(f"{group.label}:")
        for it in group.items:
            qty = f"{it.grams_to_buy:g} g"
            extra = ""
            if it.packs is not None and it.pack_size_g is not None:
                extra = f"  ({it.packs}× {it.pack_size_g:g} g)"
            cost = f"  ~ CHF {it.est_cost_chf}" if it.est_cost_chf is not None else ""
            lines.append(f"  [ ] {qty:>10}  {it.name}{extra}{cost}")
    if shopping.total_cost_chf is not None:
        lines.append("")
        lines.append("-" * 50)
        lines.append(f"Geschätzte Gesamtkosten: ~ CHF {shopping.total_cost_chf}")
    return "\n".join(lines) + "\n"


def aggregate_from_meals(db: Session, meals: Iterable[Meal]) -> dict[int, float]:
    """Hilfsfunktion für Stats-Endpoint und Tests."""
    out: dict[int, float] = defaultdict(float)
    for m in meals:
        for ing in m.ingredients:
            out[ing.product_id] += ing.grams
    return dict(out)
