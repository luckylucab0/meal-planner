"""Router für `/api/shopping-list/{plan_id}` — JSON + `.txt`-Export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Meal, MealPlan
from app.schemas.shopping_list import ShoppingGroup, ShoppingItem, ShoppingListResponse
from app.services import shopping_list as shopping_service

router = APIRouter(prefix="/api/shopping-list", tags=["shopping-list"])


def _load_plan(db: Session, plan_id: int) -> MealPlan:
    plan = db.scalars(
        select(MealPlan)
        .where(MealPlan.id == plan_id)
        .options(selectinload(MealPlan.meals).selectinload(Meal.ingredients))
    ).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


def _to_response(data: shopping_service.ShoppingList) -> ShoppingListResponse:
    return ShoppingListResponse(
        plan_id=data.plan_id,
        week_start=data.week_start,  # Pydantic akzeptiert ISO-String → date
        total_cost_chf=data.total_cost_chf,
        groups=[
            ShoppingGroup(
                category=g.category,
                label=g.label,
                items=[
                    ShoppingItem(
                        product_id=it.product_id,
                        name=it.name,
                        category=it.category,
                        grams_needed=it.grams_needed,
                        grams_to_buy=it.grams_to_buy,
                        packs=it.packs,
                        pack_size_g=it.pack_size_g,
                        est_cost_chf=it.est_cost_chf,
                    )
                    for it in g.items
                ],
            )
            for g in data.groups
        ],
    )


# `.txt`-Route muss vor der generischen `/{plan_id}` stehen, damit FastAPI
# nicht versucht, "1.txt" als int zu parsen.
@router.get("/{plan_id}.txt", response_class=PlainTextResponse)
def get_shopping_list_txt(plan_id: int, db: Session = Depends(get_db)) -> PlainTextResponse:
    plan = _load_plan(db, plan_id)
    data = shopping_service.build_shopping_list(db, plan)
    return PlainTextResponse(
        shopping_service.render_txt(data),
        headers={"Content-Disposition": f'attachment; filename="einkauf-{data.week_start}.txt"'},
    )


@router.get("/{plan_id}", response_model=ShoppingListResponse)
def get_shopping_list(plan_id: int, db: Session = Depends(get_db)) -> ShoppingListResponse:
    plan = _load_plan(db, plan_id)
    data = shopping_service.build_shopping_list(db, plan)
    return _to_response(data)
