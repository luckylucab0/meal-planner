"""Router für `/api/products` — CRUD auf der lokalen Zutaten-Bibliothek + OFF-Lookup.

Die Bibliothek dient als Cache für Open-Food-Facts-Treffer und als Sammelort
für vom Agent oder manuell eingepflegte Zutaten. Löschen ist nur möglich,
solange das Produkt von keiner Mahlzeit referenziert wird (FK `RESTRICT`).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas.product import (
    ProductCreate,
    ProductLookupRequest,
    ProductLookupResponse,
    ProductRead,
    ProductUpdate,
)
from app.services import openfoodfacts

router = APIRouter(prefix="/api/products", tags=["products"])


def _get_or_404(db: Session, product_id: int) -> Product:
    row = db.get(Product, product_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return row


@router.get("", response_model=list[ProductRead])
def list_products(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Volltextsuche auf name/normalized_name."),
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Product]:
    stmt = select(Product)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Product.name).like(like), Product.name_normalized.like(like)))
    if category:
        stmt = stmt.where(Product.category == category)
    stmt = stmt.order_by(Product.name).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    normalized = Product.normalize_name(payload.name)
    existing = db.scalars(select(Product).where(Product.name_normalized == normalized)).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Produkt '{payload.name}' existiert bereits.")
    row = Product(
        name=payload.name.strip(),
        name_normalized=normalized,
        category=payload.category,
        default_unit=payload.default_unit,
        kcal_per_100g=payload.kcal_per_100g,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
        typical_pack_size_g=payload.typical_pack_size_g,
        est_price_chf=payload.est_price_chf,
        source="manual",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    return _get_or_404(db, product_id)


@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    row = _get_or_404(db, product_id)
    new_normalized = Product.normalize_name(payload.name)
    if new_normalized != row.name_normalized:
        clash = db.scalars(
            select(Product).where(Product.name_normalized == new_normalized)
        ).one_or_none()
        if clash is not None and clash.id != product_id:
            raise HTTPException(
                status_code=409, detail=f"Produkt '{payload.name}' existiert bereits."
            )
    row.name = payload.name.strip()
    row.name_normalized = new_normalized
    row.category = payload.category
    row.default_unit = payload.default_unit
    row.kcal_per_100g = payload.kcal_per_100g
    row.protein_g = payload.protein_g
    row.carbs_g = payload.carbs_g
    row.fat_g = payload.fat_g
    row.typical_pack_size_g = payload.typical_pack_size_g
    row.est_price_chf = payload.est_price_chf
    row.source = "manual"
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> Response:
    row = _get_or_404(db, product_id)
    db.delete(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Produkt ist in Mahlzeiten referenziert und kann nicht gelöscht werden.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/lookup", response_model=ProductLookupResponse)
def lookup_product(
    payload: ProductLookupRequest, db: Session = Depends(get_db)
) -> ProductLookupResponse:
    """Lokal-first; bei Miss → Open Food Facts; sonst not_found."""
    product, source = openfoodfacts.lookup_or_fetch(db, payload.name, force_remote=payload.force_remote)
    if product is None:
        return ProductLookupResponse(source_resolved="not_found", product=None)
    db.commit()
    db.refresh(product)
    return ProductLookupResponse(
        source_resolved="local" if source == "local" else "off",
        product=ProductRead.model_validate(product),
    )
