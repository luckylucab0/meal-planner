"""ORM-Modell `meal_history` — Snapshot vergangener Mahlzeiten für Wiederholungs-Schutz.

Wird beim Speichern eines Plans pro Mahlzeit befüllt. Bewusst denormalisiert
(nur `title` + `date` + `slot` + Plan-Referenz), damit das Tool
`get_recent_meal_history` ohne Joins schnell die letzten 4 Wochen liefern kann
und Plan-Löschungen die Historie nicht reissen (Plan-FK ist nullable).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MealHistory(Base):
    __tablename__ = "meal_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("meal_plans.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
