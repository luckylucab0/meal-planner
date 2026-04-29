"""Pydantic-Schemas für `/api/plans`."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Slot = Literal["lunch", "dinner"]


class SlotRequest(BaseModel):
    """Eine zu planende Mahlzeit (Datum + Slot)."""

    date: date_type
    slot: Slot


class PlanGenerateRequest(BaseModel):
    """Request-Body für `POST /api/plans/generate`.

    `slots` ist die Liste der zu planenden Mittag-/Abend-Mahlzeiten —
    nur Tage, an denen der User zuhause kocht.
    """

    week_start: date_type
    slots: list[SlotRequest] = Field(min_length=1, max_length=14)
    # User-Eingabe wird in den LLM-Prompt eingebettet — Länge begrenzt
    # gegen DoS/Token-Burn und um den Injektions-Angriffsraum klein zu halten.
    notes: str | None = Field(default=None, max_length=2000)


class IngredientRead(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    product_id: int
    name: str
    grams: float
    category: str
    est_price_chf: Decimal | None


class MealRead(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: int
    date: date_type
    slot: Slot
    title: str
    instructions: str
    prep_time_min: int
    macros: dict[str, float | bool]
    estimated_cost_chf: Decimal | None
    uses_leftovers_from_id: int | None
    ingredients: list[IngredientRead]


class PlanRead(BaseModel):
    """Vollständiger Plan inklusive Mahlzeiten und Zutaten."""

    model_config = ConfigDict(from_attributes=False)

    id: int
    week_start: date_type
    generated_at: datetime
    notes: str | None
    weekly_totals: dict[str, float | None]
    meals: list[MealRead]


class PlanSummary(BaseModel):
    """Schlanke Form für die Historie-Liste."""

    id: int
    week_start: date_type
    generated_at: datetime
    notes: str | None
    weekly_totals: dict[str, float | None]
    meals_count: int
