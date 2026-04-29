"""Pydantic-Schemas für `/api/stats`."""

from __future__ import annotations

from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field


class DailyMacros(BaseModel):
    """Aggregierte Makros eines einzelnen Tages."""

    date: date_type
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    meals_count: int


class MacrosRange(BaseModel):
    """Antwort für `/api/stats/macros`. `from` ist Python-Keyword → Alias."""

    model_config = ConfigDict(populate_by_name=True)

    from_date: date_type = Field(serialization_alias="from", validation_alias="from")
    to: date_type
    kcal_target: int
    protein_target_g: int
    days: list[DailyMacros]
