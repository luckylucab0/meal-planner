"""ORM-Modell `user_preferences` (Singleton, id=1).

Hält Vorlieben, Fitness-Ziele und Diät-Tags des Users. Listen werden als
JSON gespeichert (SQLite-portabel via `JSON`-Typ). Singleton, weil die
Anwendung Single-User ist — die API-Routen behandeln id=1 als implizit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Lebensmittel-Listen — JSON-Arrays mit normalisierten Namen.
    whitelist_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    blacklist_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Fitness — Werte aus dem Set {muskelaufbau, abnehmen, erhaltung, ausdauer}.
    fitness_goal: Mapped[str] = mapped_column(String(32), default="erhaltung", nullable=False)
    kcal_target: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    protein_target_g: Mapped[int] = mapped_column(Integer, default=120, nullable=False)

    # Praktisches.
    max_prep_min: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    weekly_budget_chf: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Diät-Tags wie 'vegetarisch', 'low-carb', 'glutenfrei'.
    diet_tags_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def default_payload(cls) -> dict[str, Any]:
        """Default-Werte für die initiale Singleton-Zeile (id=1)."""
        return {
            "id": 1,
            "whitelist_json": [],
            "blacklist_json": [],
            "fitness_goal": "erhaltung",
            "kcal_target": 2000,
            "protein_target_g": 120,
            "max_prep_min": 45,
            "weekly_budget_chf": None,
            "diet_tags_json": [],
        }
