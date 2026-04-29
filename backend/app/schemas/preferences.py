"""Pydantic-Schemas für `/api/preferences`.

`PreferencesRead` ist die Antwort-Form, `PreferencesUpdate` validiert das
Request-Body von `PUT /api/preferences`. `fitness_goal` ist auf einen festen
Set begrenzt; `diet_tags` ist offen, weil der User auch eigene Tags
einführen können soll.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FitnessGoal = Literal["muskelaufbau", "abnehmen", "erhaltung", "ausdauer"]


class PreferencesRead(BaseModel):
    """Antwort-Schema (saubere Public-API-Namen ohne `_json`-Suffix)."""

    model_config = ConfigDict(from_attributes=False)

    whitelist: list[str]
    blacklist: list[str]
    fitness_goal: FitnessGoal
    kcal_target: int
    protein_target_g: int
    max_prep_min: int
    weekly_budget_chf: Decimal | None
    diet_tags: list[str]
    updated_at: datetime


class PreferencesUpdate(BaseModel):
    """Request-Schema für `PUT /api/preferences` — alle Felder erforderlich."""

    whitelist: list[str] = Field(default_factory=list, max_length=100)
    blacklist: list[str] = Field(default_factory=list, max_length=100)
    fitness_goal: FitnessGoal = "erhaltung"
    kcal_target: int = Field(default=2000, ge=800, le=6000)
    protein_target_g: int = Field(default=120, ge=20, le=400)
    max_prep_min: int = Field(default=45, ge=5, le=240)
    weekly_budget_chf: Decimal | None = Field(default=None, ge=0, le=10000)
    diet_tags: list[str] = Field(default_factory=list, max_length=20)
