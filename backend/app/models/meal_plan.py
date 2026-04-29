"""ORM-Modelle `meal_plans`, `meals`, `meal_ingredients`.

- `meal_plans` ist der Header pro Woche (eine Zeile, frei wählbares Start-Datum).
- `meals` enthält je Slot (lunch/dinner) eine Mahlzeit; `uses_leftovers_from_id`
  zeigt auf eine vorhergehende Mahlzeit, deren Reste verwertet werden.
- `meal_ingredients` ist die n:m-Verknüpfung zu `products` mit Mengenangabe in
  Gramm.

Cascade-Verhalten: Löschen eines Plans löscht alle Mahlzeiten und deren
Zutaten-Verknüpfungen automatisch (`ondelete='CASCADE'` + `cascade='all, delete-orphan'`).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    weekly_totals_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    meals: Mapped[list[Meal]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="Meal.date, Meal.slot",
    )


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot: Mapped[str] = mapped_column(String(16), nullable=False)  # 'lunch' | 'dinner'
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prep_time_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    macros_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    estimated_cost_chf: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    uses_leftovers_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("meals.id", ondelete="SET NULL"), nullable=True
    )

    plan: Mapped[MealPlan] = relationship(back_populates="meals")
    ingredients: Mapped[list[MealIngredient]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
    )


class MealIngredient(Base):
    __tablename__ = "meal_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    grams: Mapped[float] = mapped_column(Float, nullable=False)

    meal: Mapped[Meal] = relationship(back_populates="ingredients")
