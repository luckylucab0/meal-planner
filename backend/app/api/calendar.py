"""Router für `/api/calendar` — `.ics`-Export und CalDAV-Sync.

CalDAV-Sync wird in Schritt 12 ergänzt.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Meal, MealPlan, Product
from app.services import ics_export

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
