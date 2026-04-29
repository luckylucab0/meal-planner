"""Router für `/api/plans` — Generieren, Abrufen, Historie, Regenerate.

Plan-Generierung baut einen frischen `Anthropic`-Client und delegiert an
`MealAgent.generate_plan()`. Wenn `ANTHROPIC_API_KEY` fehlt, antwortet
der Endpoint mit 503 — so erkennt das Frontend Konfigurationsprobleme früh.

`regenerate` wirft die alte Mahlzeit weg, lässt den Agent eine neue für
denselben Slot bauen und kopiert sie in den ursprünglichen Plan zurück
(das gerade neu generierte Plan-Wrapper wird wieder gelöscht).
"""

from __future__ import annotations

from datetime import date as date_type
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.exceptions import AgentPlanningError
from app.models import Meal, MealHistory, MealIngredient, MealPlan, Product
from app.schemas.plans import (
    IngredientRead,
    MealRead,
    PlanGenerateRequest,
    PlanRead,
    PlanSummary,
)
from app.services.meal_agent import MealAgent, PlanRequest

if TYPE_CHECKING:
    pass

router = APIRouter(prefix="/api/plans", tags=["plans"])


# ── Anthropic-Client ──────────────────────────────────────────────────────


def _get_anthropic_client() -> object:
    """Lazy-Import + Konstruktion. Trennt Test-Pfade von der echten SDK."""
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY ist nicht gesetzt — Plan-Generierung deaktiviert.",
        )
    from anthropic import Anthropic  # noqa: PLC0415

    return Anthropic(api_key=settings.anthropic_api_key)


# Test-Override-Hook: pytest-Fixtures schreiben hier einen Fake-Client rein.
def _agent_factory(db: Session) -> MealAgent:
    return MealAgent(client=_get_anthropic_client(), db=db)


# ── Mapping-Helpers ───────────────────────────────────────────────────────


def _meal_to_read(db: Session, meal: Meal) -> MealRead:
    ings: list[IngredientRead] = []
    for mi in meal.ingredients:
        product = db.get(Product, mi.product_id)
        ings.append(
            IngredientRead(
                product_id=mi.product_id,
                name=product.name if product else f"#{mi.product_id}",
                grams=mi.grams,
                category=product.category if product else "sonstiges",
                est_price_chf=product.est_price_chf if product else None,
            )
        )
    return MealRead(
        id=meal.id,
        date=meal.date,
        slot=meal.slot,  # type: ignore[arg-type]
        title=meal.title,
        instructions=meal.instructions,
        prep_time_min=meal.prep_time_min,
        macros=dict(meal.macros_json),
        estimated_cost_chf=meal.estimated_cost_chf,
        uses_leftovers_from_id=meal.uses_leftovers_from_id,
        ingredients=ings,
    )


def _plan_to_read(db: Session, plan: MealPlan) -> PlanRead:
    return PlanRead(
        id=plan.id,
        week_start=plan.week_start,
        generated_at=plan.generated_at,
        notes=plan.notes,
        weekly_totals={k: v for k, v in plan.weekly_totals_json.items()},
        meals=[_meal_to_read(db, m) for m in plan.meals],
    )


def _load_plan(db: Session, plan_id: int) -> MealPlan:
    plan = db.scalars(
        select(MealPlan)
        .where(MealPlan.id == plan_id)
        .options(selectinload(MealPlan.meals).selectinload(Meal.ingredients))
    ).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/generate", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def generate_plan(payload: PlanGenerateRequest, db: Session = Depends(get_db)) -> PlanRead:
    request = PlanRequest(
        week_start=payload.week_start,
        slots=[(s.date, s.slot) for s in payload.slots],
        notes=payload.notes,
    )
    agent = _agent_factory(db)
    try:
        plan_id = agent.generate_plan(request)
    except AgentPlanningError as exc:
        logger.warning("Plan-Generierung fehlgeschlagen: {}", exc)
        raise HTTPException(status_code=502, detail=f"Agent-Fehler: {exc}") from exc

    plan = _load_plan(db, plan_id)
    return _plan_to_read(db, plan)


@router.get("/current", response_model=PlanRead | None)
def get_current_plan(db: Session = Depends(get_db)) -> PlanRead | None:
    plan = db.scalars(
        select(MealPlan)
        .order_by(MealPlan.generated_at.desc())
        .options(selectinload(MealPlan.meals).selectinload(Meal.ingredients))
        .limit(1)
    ).one_or_none()
    if plan is None:
        return None
    return _plan_to_read(db, plan)


@router.get("/week/{week_start}", response_model=PlanRead | None)
def get_plan_by_week(week_start: date_type, db: Session = Depends(get_db)) -> PlanRead | None:
    plan = db.scalars(
        select(MealPlan)
        .where(MealPlan.week_start == week_start)
        .order_by(MealPlan.generated_at.desc())
        .options(selectinload(MealPlan.meals).selectinload(Meal.ingredients))
        .limit(1)
    ).one_or_none()
    if plan is None:
        return None
    return _plan_to_read(db, plan)


@router.get("/history", response_model=list[PlanSummary])
def list_plans(
    db: Session = Depends(get_db), limit: int = Query(default=10, ge=1, le=100)
) -> list[PlanSummary]:
    plans = db.scalars(
        select(MealPlan).order_by(MealPlan.week_start.desc()).limit(limit)
    ).all()
    return [
        PlanSummary(
            id=p.id,
            week_start=p.week_start,
            generated_at=p.generated_at,
            notes=p.notes,
            weekly_totals={k: v for k, v in p.weekly_totals_json.items()},
            meals_count=len(p.meals),
        )
        for p in plans
    ]


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: int, db: Session = Depends(get_db)) -> PlanRead:
    return _plan_to_read(db, _load_plan(db, plan_id))


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_plan(plan_id: int, db: Session = Depends(get_db)) -> Response:
    plan = db.get(MealPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    db.delete(plan)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{plan_id}/meals/{meal_id}/regenerate", response_model=MealRead)
def regenerate_meal(plan_id: int, meal_id: int, db: Session = Depends(get_db)) -> MealRead:
    plan = _load_plan(db, plan_id)
    target = next((m for m in plan.meals if m.id == meal_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Meal {meal_id} not in plan {plan_id}")

    target_date: date_type = target.date
    target_slot: str = target.slot

    # Agent baut einen Mini-Plan (1 Slot) und gibt dessen ID zurück.
    agent = _agent_factory(db)
    try:
        mini_plan_id = agent.generate_plan(
            PlanRequest(
                week_start=plan.week_start,
                slots=[(target_date, target_slot)],  # type: ignore[list-item]
                notes=f"Regenerate für {target_date.isoformat()} {target_slot}.",
            )
        )
    except AgentPlanningError as exc:
        raise HTTPException(status_code=502, detail=f"Agent-Fehler: {exc}") from exc

    mini_plan = _load_plan(db, mini_plan_id)
    new_meal = mini_plan.meals[0] if mini_plan.meals else None
    if new_meal is None:
        raise HTTPException(status_code=502, detail="Agent hat keine Mahlzeit erzeugt.")

    # Neue Mahlzeit in den Original-Plan kopieren, alte ersetzen.
    target.title = new_meal.title
    target.instructions = new_meal.instructions
    target.prep_time_min = new_meal.prep_time_min
    target.macros_json = dict(new_meal.macros_json)
    target.estimated_cost_chf = new_meal.estimated_cost_chf
    db.query(MealIngredient).filter(MealIngredient.meal_id == target.id).delete()
    db.flush()
    for mi in new_meal.ingredients:
        db.add(MealIngredient(meal_id=target.id, product_id=mi.product_id, grams=mi.grams))
    db.add(MealHistory(date=target.date, slot=target.slot, title=target.title, plan_id=plan.id))

    # Mini-Plan + dessen History wieder löschen.
    db.delete(mini_plan)
    db.query(MealHistory).filter(MealHistory.plan_id == mini_plan_id).delete()
    db.commit()

    refreshed = db.get(Meal, target.id)
    assert refreshed is not None
    return _meal_to_read(db, refreshed)
