"""ORM-Modell `products` — Zutaten-Cache.

Quellen: Open Food Facts (`source='off'`), Claude-Agent-Schätzung
(`source='agent'`) und manuelle Pflege (`source='manual'`). Nährwerte
sind je 100 g angegeben — die Aggregations-Logik in `services/nutrition.py`
skaliert linear auf die tatsächlich verbrauchte Menge.

`name_normalized` ist der lowercase-trimmed Name und dient als Primär-Key
für die Lookup-Strategie (lokale DB → OFF → Agent-Fallback).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    name_normalized: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True, index=True
    )

    # Generische Supermarkt-Kategorien — siehe `services/shopping_list.py`
    # für die Sortier-Reihenfolge.
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="sonstiges", index=True)
    default_unit: Mapped[str] = mapped_column(String(16), nullable=False, default="g")

    # Nährwerte je 100 g.
    kcal_per_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Optional: typische Verkaufseinheit (z.B. 250 g Hack), Schweizer Preis-Schätzung.
    typical_pack_size_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_price_chf: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Provenance.
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="agent")
    off_barcode: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    off_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @staticmethod
    def normalize_name(value: str) -> str:
        """Lower-case, getrimmt, mehrfach-Whitespace zu einem Space."""
        return " ".join(value.lower().split())
