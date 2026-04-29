"""Router für `/api/calendar` — `.ics`-Export und CalDAV-Sync."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.exceptions import CalDavSyncError
from app.models import AppSettings, Meal, MealPlan, Product
from app.schemas.settings import CalDavSyncResult
from app.services import caldav_sync, ics_export

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


def _load_plan(db: Session, plan_id: int) -> MealPlan:
    plan = db.scalars(
        select(MealPlan)
        .where(MealPlan.id == plan_id)
        .options(selectinload(MealPlan.meals).selectinload(Meal.ingredients))
    ).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


@router.get("/{plan_id}.ics")
def get_plan_ics(plan_id: int, db: Session = Depends(get_db)) -> Response:
    plan = _load_plan(db, plan_id)
    product_ids = ics_export.collect_ingredient_names(plan.meals)
    rows = db.scalars(select(Product).where(Product.id.in_(product_ids))).all() if product_ids else []
    names = {p.id: p.name for p in rows}
    body = ics_export.build_calendar(plan, names)
    return Response(
        content=body,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="meal-plan-{plan.week_start}.ics"'},
    )


@router.post("/sync-apple/{plan_id}", response_model=CalDavSyncResult)
def sync_to_apple(plan_id: int, db: Session = Depends(get_db)) -> CalDavSyncResult:
    plan = _load_plan(db, plan_id)
    settings_row = db.get(AppSettings, 1)
    if settings_row is None or not settings_row.caldav_enabled:
        raise HTTPException(status_code=409, detail="CalDAV ist nicht aktiviert.")

    product_ids = ics_export.collect_ingredient_names(plan.meals)
    products = (
        {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()}
        if product_ids
        else {}
    )

    try:
        stats = caldav_sync.sync_plan_to_icloud(settings_row, plan, products)
    except CalDavSyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return CalDavSyncResult(
        created=stats.created,
        updated=stats.updated,
        plan_id=plan.id,
        calendar_name=settings_row.caldav_calendar_name,
    )
