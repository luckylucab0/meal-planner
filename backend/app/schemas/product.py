"""Pydantic-Schemas für `/api/products`."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProductSource = Literal["off", "agent", "manual"]


class ProductRead(BaseModel):
    """Antwort-Form."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_normalized: str
    category: str
    default_unit: str
    kcal_per_100g: float
    protein_g: float
    carbs_g: float
    fat_g: float
    typical_pack_size_g: float | None
    est_price_chf: Decimal | None
    source: ProductSource
    off_barcode: str | None
    off_fetched_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    """Manuelles Anlegen einer Zutat."""

    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="sonstiges", max_length=64)
    default_unit: str = Field(default="g", max_length=16)
    kcal_per_100g: float = Field(ge=0, le=2000)
    protein_g: float = Field(ge=0, le=200)
    carbs_g: float = Field(ge=0, le=200)
    fat_g: float = Field(ge=0, le=200)
    typical_pack_size_g: float | None = Field(default=None, ge=0)
    est_price_chf: Decimal | None = Field(default=None, ge=0)


class ProductUpdate(ProductCreate):
    """Manuelle Anpassung — selbe Felder wie `Create`."""


class ProductLookupRequest(BaseModel):
    """Request-Body für `POST /api/products/lookup`."""

    name: str = Field(min_length=1, max_length=200)
    force_remote: bool = Field(default=False, description="Open Food Facts neu abfragen, auch wenn lokal vorhanden.")


class ProductLookupResponse(BaseModel):
    """Antwort mit Produkt + Hinweis, woher es kam."""

    source_resolved: Literal["local", "off", "not_found"]
    product: ProductRead | None
