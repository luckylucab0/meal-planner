"""Tests für `MealAgent` mit gescripteten Anthropic-Responses und einer
isolierten In-Memory-DB.

Wir prüfen vor allem:
- Tool-Dispatch funktioniert (lokaler Produkt-Lookup, calculate_nutrition,
  save_meal_plan).
- Plan + Meals + MealIngredients + MealHistory landen in der DB.
- Validierung der Stop-Bedingungen (no save → AgentPlanningError).
"""

from __future__ import annotations

import copy
from collections import deque
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions import AgentPlanningError
from app.models import (
    Meal,
    MealHistory,
    MealIngredient,
    MealPlan,
    Product,
    UserPreferences,
)
from app.services.meal_agent import MealAgent, PlanRequest


# ── Fake Anthropic ─────────────────────────────────────────────────────────


def _tool_use(tool_id: str, name: str, args: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=args)


def _text(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _response(content: list[Any], stop_reason: str) -> SimpleNamespace:
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class _FakeMessages:
    def __init__(self, responses: deque[Any]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        # Snapshot, weil der Agent das `messages`-Listenobjekt
        # zwischen Calls mutiert (Referenzweitergabe).
        self.calls.append(copy.deepcopy(kwargs))
        if not self._responses:
            raise AssertionError("Mehr Anthropic-Calls als gescripted")
        return self._responses.popleft()


class FakeAnthropic:
    def __init__(self, responses: list[Any]) -> None:
        self.messages = _FakeMessages(deque(responses))


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def _seed(db) -> int:
    """Legt Default-Preferences und ein lokal verfügbares Produkt 'Quinoa' an."""
    db.add(UserPreferences(**UserPreferences.default_payload()))
    quinoa = Product(
        name="Quinoa",
        name_normalized="quinoa",
        category="getreide",
        default_unit="g",
        kcal_per_100g=360.0,
        protein_g=14.0,
        carbs_g=64.0,
        fat_g=6.0,
        typical_pack_size_g=500.0,
        source="manual",
    )
    db.add(quinoa)
    db.commit()
    db.refresh(quinoa)
    return quinoa.id


# ── Tests ──────────────────────────────────────────────────────────────────


def test_agent_runs_loop_and_persists_plan(db) -> None:
    quinoa_id = _seed(db)

    fake = FakeAnthropic(
        [
            _response(
                [_tool_use("t1", "lookup_product", {"name": "Quinoa"})],
                stop_reason="tool_use",
            ),
            _response(
                [
                    _tool_use(
                        "t2",
                        "save_meal_plan",
                        {
                            "week_start": "2026-05-04",
                            "notes": "Test-Plan",
                            "meals": [
                                {
                                    "date": "2026-05-04",
                                    "slot": "lunch",
                                    "title": "Quinoa-Bowl",
                                    "instructions": "1. Quinoa kochen.\n2. Anrichten.",
                                    "prep_time_min": 20,
                                    "estimated_cost_chf": 4.5,
                                    "ingredients": [
                                        {"product_id": quinoa_id, "grams": 80}
                                    ],
                                }
                            ],
                        },
                    )
                ],
                stop_reason="tool_use",
            ),
            _response([_text("Plan gespeichert.")], stop_reason="end_turn"),
        ]
    )

    agent = MealAgent(client=fake, db=db, model="test-model")
    plan_id = agent.generate_plan(
        PlanRequest(
            week_start=date(2026, 5, 4),
            slots=[(date(2026, 5, 4), "lunch")],
        )
    )

    assert plan_id is not None
    plan = db.get(MealPlan, plan_id)
    assert plan is not None
    assert plan.notes == "Test-Plan"

    meals = db.query(Meal).filter_by(plan_id=plan.id).all()
    assert len(meals) == 1
    meal = meals[0]
    assert meal.title == "Quinoa-Bowl"
    assert meal.slot == "lunch"
    # 80g Quinoa @ 360 kcal/100g = 288 kcal
    assert meal.macros_json["kcal"] == pytest.approx(288.0, rel=0.01)
    assert meal.estimated_cost_chf is not None
    assert float(meal.estimated_cost_chf) == 4.5

    ingredients = db.query(MealIngredient).filter_by(meal_id=meal.id).all()
    assert len(ingredients) == 1
    assert ingredients[0].product_id == quinoa_id
    assert ingredients[0].grams == 80

    history = db.query(MealHistory).filter_by(plan_id=plan.id).all()
    assert len(history) == 1
    assert history[0].title == "Quinoa-Bowl"

    # Plan-totals sind korrekt aggregiert.
    totals = plan.weekly_totals_json
    assert totals["avg_kcal"] == pytest.approx(288.0, rel=0.01)


def test_agent_raises_when_save_never_called(db) -> None:
    _seed(db)
    fake = FakeAnthropic([_response([_text("Ich überlege noch.")], stop_reason="end_turn")])
    agent = MealAgent(client=fake, db=db, model="test-model")
    with pytest.raises(AgentPlanningError):
        agent.generate_plan(
            PlanRequest(week_start=date(2026, 5, 4), slots=[(date(2026, 5, 4), "lunch")])
        )


def test_agent_dispatches_calculate_nutrition(db) -> None:
    quinoa_id = _seed(db)

    fake = FakeAnthropic(
        [
            _response(
                [
                    _tool_use(
                        "t1",
                        "calculate_nutrition",
                        {"ingredients": [{"product_id": quinoa_id, "grams": 100}]},
                    )
                ],
                stop_reason="tool_use",
            ),
            _response(
                [
                    _tool_use(
                        "t2",
                        "save_meal_plan",
                        {
                            "week_start": "2026-05-04",
                            "meals": [
                                {
                                    "date": "2026-05-04",
                                    "slot": "dinner",
                                    "title": "Quinoa pur",
                                    "instructions": "Kochen.",
                                    "prep_time_min": 15,
                                    "ingredients": [
                                        {"product_id": quinoa_id, "grams": 100}
                                    ],
                                }
                            ],
                        },
                    )
                ],
                stop_reason="tool_use",
            ),
            _response([_text("Fertig.")], stop_reason="end_turn"),
        ]
    )

    agent = MealAgent(client=fake, db=db, model="test-model")
    plan_id = agent.generate_plan(
        PlanRequest(week_start=date(2026, 5, 4), slots=[(date(2026, 5, 4), "dinner")])
    )
    assert plan_id is not None

    # Tool-Result vom calculate_nutrition wurde an Claude zurückgegeben — wir
    # prüfen das indirekt via 3. Anthropic-Call (er sollte den tool_result als
    # Inhalt der user-Message enthalten).
    third_call = fake.messages.calls[1]
    last_user_msg = third_call["messages"][-1]
    assert last_user_msg["role"] == "user"
    assert any(item["type"] == "tool_result" for item in last_user_msg["content"])
