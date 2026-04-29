"""Pydantic-Schemas für `/api/shopping-list`."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class ShoppingItem(BaseModel):
    product_id: int
    name: str
    category: str
    grams_needed: float
    grams_to_buy: float
    packs: int | None
    pack_size_g: float | None
    est_cost_chf: Decimal | None


class ShoppingGroup(BaseModel):
    category: str
    label: str
    items: list[ShoppingItem]


class ShoppingListResponse(BaseModel):
    plan_id: int
    week_start: date_type
    groups: list[ShoppingGroup]
    total_cost_chf: Decimal | None
