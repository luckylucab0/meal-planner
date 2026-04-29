"""Claude-Agent — Tool-Use-Loop zur Plan-Generierung.

Architektur:
- `TOOL_DEFINITIONS` beschreibt die Schemas, die der Agent aufrufen kann.
- `MealAgent` koppelt den Anthropic-Client mit einer DB-Session und
  dispatcht jeden Tool-Call an die passende Python-Implementation.
- `generate_plan(request)` führt den Multi-Turn-Loop aus und gibt die
  ID des gespeicherten `MealPlan` zurück.

Der Anthropic-Client ist injiziert, damit Tests einen Fake reinhängen können.
Das Modell ist in `settings.model_planner` konfigurierbar (default Opus 4.7).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal, Protocol

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import AgentPlanningError, OpenFoodFactsError
from app.models import (
    Meal,
    MealHistory,
    MealIngredient,
    MealPlan,
    Product,
    UserPreferences,
)
from app.services import nutrition, openfoodfacts

Slot = Literal["lunch", "dinner"]

MAX_TOOL_TURNS = 25
MAX_TOKENS_PER_CALL = 4096


# ── System-Prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Du bist ein erfahrener Schweizer Ernährungs-Coach und Hobby-Koch. Deine
Aufgabe ist es, persönliche Mittag- und Abendessen-Pläne zu erstellen.

Kontext und Stil:
- Wir sind in der Schweiz (Region Zürich/Bülach). Preise rechnest du in CHF
  und orientierst dich am Schweizer Preisniveau (Migros/Coop-Niveau).
- Achte auf saisonale Verfügbarkeit. Im Frühling z.B. Spargel, Bärlauch,
  Radieschen; im Winter Wurzelgemüse, Kohl, Lauch.
- Bevorzuge Zutaten, die in einer typischen Schweizer Filiale problemlos
  erhältlich sind. Vermeide exotische Importware ohne Notwendigkeit.

Vorgehen:
1. Lade zuerst die User-Vorlieben mit `get_user_preferences`.
2. Optional: prüfe `get_recent_meal_history`, um Wiederholungen zu vermeiden.
3. Plane die angefragten Mahlzeiten. Für jede Zutat:
   - rufe `lookup_product` auf (lokal-first, fällt auf Open Food Facts zurück);
   - **Wichtig:** wenn `lookup_product` `found: false` ODER
     `source_resolved: "unavailable"` (Open Food Facts gerade down) liefert,
     rufe **sofort** im selben Turn `upsert_product` mit deinen eigenen
     Makro-Werten auf. Niemals stehenbleiben oder den Loop abbrechen, nur
     weil OFF nicht antwortet — du hast genug Ernährungswissen, um
     realistische kcal/Protein/Carbs/Fett-Werte pro 100 g zu schätzen.
4. Pro Mahlzeit: rufe `calculate_nutrition` auf, um die Makros zu validieren.
5. Wenn alle Mahlzeiten geplant sind, rufe **einmal** `save_meal_plan` mit
   der vollständigen Struktur auf.

**Verbindliche Endbedingung:** Du bist erst fertig, wenn `save_meal_plan`
erfolgreich durchgelaufen ist (du erhältst eine `plan_id` zurück). Beende
den Loop NICHT mit einer reinen Text-Antwort, ausser bei einem echten,
nicht behebbaren Konflikt (z.B. Whitelist und Blacklist sind direkt
widersprüchlich); in dem Fall: kurze Erklärung, dann Stop.

Qualitätskriterien:
- Halte das Kalorien-Ziel pro Tag mit Toleranz ±15 % ein.
- Erreiche das Protein-Ziel möglichst präzise (lieber leicht über, nie deutlich darunter).
- Respektiere Blacklist (Allergien!) strikt — kein einziges Vorkommen.
- Halte `prep_time_min` unterhalb der konfigurierten Maximalzeit.
- Bei mehreren Tagen: nutze Reste sinnvoll (z.B. übrige Pouletbrust am Folgetag).
- Variiere Hauptproteine und Beilagen über die Woche.
- Schreibe Anleitungen in 4–8 klaren, kurzen Schritten auf Deutsch.

Antworte sparsam mit Text — die eigentliche Arbeit passiert über die Tools.
"""


# ── Tool-Definitionen ──────────────────────────────────────────────────────

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_user_preferences",
        "description": "Lädt die persönlichen Vorlieben, Fitness-Ziele und Diät-Tags des Users.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_recent_meal_history",
        "description": "Liefert die letzten geplanten Mahlzeiten (default 30), um Wiederholungen zu vermeiden.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30}
            },
            "required": [],
        },
    },
    {
        "name": "lookup_product",
        "description": (
            "Schlägt eine Zutat nach. Strategie: lokale DB → Open Food Facts → Cache. "
            "Liefert product_id und Makros pro 100 g."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "upsert_product",
        "description": (
            "Legt eine Zutat manuell an (oder aktualisiert eine bestehende), wenn weder "
            "lokal noch Open Food Facts etwas finden. Du gibst Makros pro 100 g und optional "
            "typische Pack-Grösse + Schweizer Preis-Schätzung an."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "category": {"type": "string"},
                "kcal_per_100g": {"type": "number"},
                "protein_g": {"type": "number"},
                "carbs_g": {"type": "number"},
                "fat_g": {"type": "number"},
                "typical_pack_size_g": {"type": "number"},
                "est_price_chf": {"type": "number"},
            },
            "required": ["name", "kcal_per_100g", "protein_g", "carbs_g", "fat_g"],
        },
    },
    {
        "name": "calculate_nutrition",
        "description": "Aggregiert Makros einer Zutatenliste (product_id + grams).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ingredients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer"},
                            "grams": {"type": "number"},
                        },
                        "required": ["product_id", "grams"],
                    },
                }
            },
            "required": ["ingredients"],
        },
    },
    {
        "name": "save_meal_plan",
        "description": (
            "Speichert den finalen Plan. `week_start` ist der Montag der Woche. Jede "
            "Mahlzeit braucht Datum, Slot, Titel, Anleitung, Zubereitungszeit und eine "
            "Zutaten-Liste mit product_id und grams. Optional: estimated_cost_chf."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "week_start": {"type": "string", "description": "Montag der Woche, ISO-Datum."},
                "notes": {"type": "string"},
                "meals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string"},
                            "slot": {"type": "string", "enum": ["lunch", "dinner"]},
                            "title": {"type": "string"},
                            "instructions": {"type": "string"},
                            "prep_time_min": {"type": "integer"},
                            "estimated_cost_chf": {"type": "number"},
                            "ingredients": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "product_id": {"type": "integer"},
                                        "grams": {"type": "number"},
                                    },
                                    "required": ["product_id", "grams"],
                                },
                            },
                        },
                        "required": [
                            "date",
                            "slot",
                            "title",
                            "instructions",
                            "prep_time_min",
                            "ingredients",
                        ],
                    },
                },
            },
            "required": ["week_start", "meals"],
        },
    },
]


# ── Anthropic-Client-Protokoll (für Mocking) ───────────────────────────────


class _MessagesAPI(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class _AnthropicLike(Protocol):
    messages: _MessagesAPI


# ── Request-Datenklasse ────────────────────────────────────────────────────


@dataclass(slots=True)
class PlanRequest:
    """Eingabe für `MealAgent.generate_plan()`.

    `slots` ist eine Liste von (Datum, lunch/dinner)-Paaren — der Agent soll
    genau diese Mahlzeiten planen (nicht mehr, nicht weniger).
    """

    week_start: date
    slots: list[tuple[date, Slot]]
    notes: str | None = None


# ── Agent ──────────────────────────────────────────────────────────────────


class MealAgent:
    """Tool-Use-Loop gegen die Anthropic-API."""

    def __init__(self, client: _AnthropicLike, db: Session, model: str | None = None):
        self.client = client
        self.db = db
        self.model = model or settings.model_planner
        self._saved_plan_id: int | None = None

    # ─── Public API ───────────────────────────────────────────────────────

    def generate_plan(self, request: PlanRequest) -> int:
        """Führt den Multi-Turn-Loop aus, gibt die ID des gespeicherten Plans zurück."""
        prefs = self._load_preferences()
        system_blocks = self._build_system_blocks(prefs)
        user_message = self._build_user_message(request)

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"type": "text", "text": user_message}]}
        ]

        for turn in range(MAX_TOOL_TURNS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS_PER_CALL,
                system=system_blocks,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
            stop_reason = getattr(response, "stop_reason", None)
            content = list(getattr(response, "content", []))
            messages.append({"role": "assistant", "content": [_block_to_dict(b) for b in content]})

            if stop_reason != "tool_use":
                logger.info(
                    "Agent fertig nach {} Turns (stop_reason={}).", turn + 1, stop_reason
                )
                break

            tool_results = []
            for block in content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                result = self._dispatch_tool(block.name, dict(block.input or {}))
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False, default=_json_default),
                    }
                )
            messages.append({"role": "user", "content": tool_results})
        else:
            raise AgentPlanningError(
                f"Agent hat in {MAX_TOOL_TURNS} Turns keinen vollständigen Plan erzeugt."
            )

        if self._saved_plan_id is None:
            # Letzter Text-Block des Agents in die Fehlermeldung mitnehmen,
            # damit das Frontend zeigen kann, was er sagen wollte.
            last_text = ""
            for msg in reversed(messages):
                if msg.get("role") != "assistant":
                    continue
                for block in msg.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        last_text = str(block.get("text", "")).strip()
                        break
                if last_text:
                    break
            extra = f' Agent-Antwort: „{last_text[:400]}…"' if last_text else ""
            raise AgentPlanningError(
                f"Agent hat den Loop beendet, aber `save_meal_plan` nie aufgerufen.{extra}"
            )
        return self._saved_plan_id

    # ─── System-Prompt + User-Message ─────────────────────────────────────

    def _build_system_blocks(self, prefs: UserPreferences) -> list[dict[str, Any]]:
        prefs_block = (
            "Aktuelle User-Vorlieben (zur Orientierung — kann bei Bedarf "
            "auch via `get_user_preferences` abgerufen werden):\n"
            f"- Fitness-Ziel: {prefs.fitness_goal}\n"
            f"- Kalorien-Ziel pro Tag: {prefs.kcal_target} kcal\n"
            f"- Protein-Ziel pro Tag: {prefs.protein_target_g} g\n"
            f"- Max. Kochzeit: {prefs.max_prep_min} min\n"
            f"- Whitelist: {', '.join(prefs.whitelist_json) or '—'}\n"
            f"- Blacklist (strikt vermeiden!): {', '.join(prefs.blacklist_json) or '—'}\n"
            f"- Diät-Tags: {', '.join(prefs.diet_tags_json) or '—'}\n"
            f"- Wochenbudget: "
            f"{f'{prefs.weekly_budget_chf} CHF' if prefs.weekly_budget_chf else 'kein Limit'}"
        )
        return [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": prefs_block, "cache_control": {"type": "ephemeral"}},
        ]

    def _build_user_message(self, request: PlanRequest) -> str:
        slot_lines = [f"  - {d.isoformat()} {slot}" for d, slot in request.slots]
        slot_block = "\n".join(slot_lines)
        notes = f"\n\nNotizen: {request.notes}" if request.notes else ""
        return (
            f"Plane bitte folgende Mahlzeiten (Wochenstart {request.week_start.isoformat()}):\n"
            f"{slot_block}{notes}\n\n"
            "Wenn du fertig bist, ruf `save_meal_plan` mit der vollständigen Struktur auf."
        )

    # ─── Tool-Dispatch ────────────────────────────────────────────────────

    def _dispatch_tool(self, name: str, args: dict[str, Any]) -> Any:
        logger.debug("Tool-Call: {} {}", name, args)
        try:
            handler = _TOOL_HANDLERS[name]
        except KeyError:
            return {"error": f"Unbekanntes Tool: {name}"}
        try:
            return handler(self, args)
        except Exception as exc:  # noqa: BLE001 — wir reichen das an Claude weiter
            logger.warning("Tool '{}' fehlgeschlagen: {}", name, exc)
            return {"error": f"{exc.__class__.__name__}: {exc}"}

    # ─── Tool-Implementationen ────────────────────────────────────────────

    def _tool_get_user_preferences(self, _args: dict[str, Any]) -> dict[str, Any]:
        prefs = self._load_preferences()
        return {
            "fitness_goal": prefs.fitness_goal,
            "kcal_target": prefs.kcal_target,
            "protein_target_g": prefs.protein_target_g,
            "max_prep_min": prefs.max_prep_min,
            "whitelist": list(prefs.whitelist_json),
            "blacklist": list(prefs.blacklist_json),
            "diet_tags": list(prefs.diet_tags_json),
            "weekly_budget_chf": float(prefs.weekly_budget_chf) if prefs.weekly_budget_chf else None,
        }

    def _tool_get_recent_meal_history(self, args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit", 30))
        rows = self.db.scalars(
            select(MealHistory).order_by(MealHistory.date.desc()).limit(limit)
        ).all()
        return {
            "meals": [
                {"date": r.date.isoformat(), "slot": r.slot, "title": r.title} for r in rows
            ]
        }

    def _tool_lookup_product(self, args: dict[str, Any]) -> dict[str, Any]:
        name = str(args["name"])
        try:
            product, source = openfoodfacts.lookup_or_fetch(self.db, name)
        except OpenFoodFactsError as exc:
            # OFF kann transient down sein — wir liefern dem Agent einen
            # strukturierten "unavailable"-Hinweis statt eines Error-Strings,
            # damit er auf `upsert_product` umsteigt statt die Tour aufzugeben.
            logger.info("lookup_product: OFF nicht verfügbar für '{}', upsert empfohlen.", name)
            return {
                "found": False,
                "name": name,
                "source_resolved": "unavailable",
                "hint": (
                    "Open Food Facts ist nicht erreichbar. Lege die Zutat "
                    "JETZT mit `upsert_product` selbst an (Makros aus deinem "
                    "Wissen)."
                ),
                "off_error": str(exc),
            }
        if product is None:
            return {
                "found": False,
                "name": name,
                "source_resolved": source,
                "hint": (
                    "Weder lokal noch in OFF gefunden. Lege die Zutat mit "
                    "`upsert_product` an."
                ),
            }
        return {
            "found": True,
            "source_resolved": source,
            "product": _product_summary(product),
        }

    def _tool_upsert_product(self, args: dict[str, Any]) -> dict[str, Any]:
        name = str(args["name"]).strip()
        normalized = Product.normalize_name(name)
        existing = self.db.scalars(
            select(Product).where(Product.name_normalized == normalized)
        ).one_or_none()
        if existing is not None:
            existing.kcal_per_100g = float(args["kcal_per_100g"])
            existing.protein_g = float(args["protein_g"])
            existing.carbs_g = float(args["carbs_g"])
            existing.fat_g = float(args["fat_g"])
            if args.get("category"):
                existing.category = str(args["category"])
            if args.get("typical_pack_size_g") is not None:
                existing.typical_pack_size_g = float(args["typical_pack_size_g"])
            if args.get("est_price_chf") is not None:
                existing.est_price_chf = Decimal(str(args["est_price_chf"]))
            existing.source = "agent"
            self.db.flush()
            return {"product": _product_summary(existing)}

        row = Product(
            name=name,
            name_normalized=normalized,
            category=args.get("category", "sonstiges"),
            default_unit="g",
            kcal_per_100g=float(args["kcal_per_100g"]),
            protein_g=float(args["protein_g"]),
            carbs_g=float(args["carbs_g"]),
            fat_g=float(args["fat_g"]),
            typical_pack_size_g=(
                float(args["typical_pack_size_g"]) if args.get("typical_pack_size_g") is not None else None
            ),
            est_price_chf=(
                Decimal(str(args["est_price_chf"])) if args.get("est_price_chf") is not None else None
            ),
            source="agent",
        )
        self.db.add(row)
        self.db.flush()
        return {"product": _product_summary(row)}

    def _tool_calculate_nutrition(self, args: dict[str, Any]) -> dict[str, Any]:
        refs = [
            nutrition.IngredientRef(
                product_id=int(item["product_id"]), grams=float(item["grams"])
            )
            for item in args["ingredients"]
        ]
        return nutrition.calculate_macros(self.db, refs).to_dict()

    def _tool_save_meal_plan(self, args: dict[str, Any]) -> dict[str, Any]:
        week_start = date.fromisoformat(str(args["week_start"]))
        plan = MealPlan(
            week_start=week_start,
            generated_at=datetime.now(timezone.utc),
            notes=args.get("notes"),
            weekly_totals_json={},
        )
        self.db.add(plan)
        self.db.flush()

        total_kcal = 0.0
        total_protein = 0.0
        total_cost = 0.0
        days_with_meals: set[date] = set()

        for meal_dict in args["meals"]:
            meal_date = date.fromisoformat(str(meal_dict["date"]))
            ingredients = [
                nutrition.IngredientRef(int(i["product_id"]), float(i["grams"]))
                for i in meal_dict["ingredients"]
            ]
            macros = nutrition.calculate_macros(self.db, ingredients)
            cost = meal_dict.get("estimated_cost_chf")
            meal = Meal(
                plan_id=plan.id,
                date=meal_date,
                slot=str(meal_dict["slot"]),
                title=str(meal_dict["title"]),
                instructions=str(meal_dict.get("instructions", "")),
                prep_time_min=int(meal_dict.get("prep_time_min", 0)),
                macros_json=macros.to_dict(),
                estimated_cost_chf=Decimal(str(cost)) if cost is not None else None,
            )
            self.db.add(meal)
            self.db.flush()

            for ref in ingredients:
                self.db.add(
                    MealIngredient(meal_id=meal.id, product_id=ref.product_id, grams=ref.grams)
                )
            self.db.add(
                MealHistory(
                    date=meal_date, slot=meal.slot, title=meal.title, plan_id=plan.id
                )
            )
            total_kcal += macros.kcal
            total_protein += macros.protein_g
            if cost is not None:
                total_cost += float(cost)
            days_with_meals.add(meal_date)

        days = max(len(days_with_meals), 1)
        plan.weekly_totals_json = {
            "avg_kcal": round(total_kcal / days, 1),
            "avg_protein_g": round(total_protein / days, 1),
            "total_cost_chf": round(total_cost, 2) if total_cost else None,
        }
        self.db.commit()
        self._saved_plan_id = plan.id
        return {"plan_id": plan.id}

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _load_preferences(self) -> UserPreferences:
        prefs = self.db.get(UserPreferences, 1)
        if prefs is None:
            prefs = UserPreferences(**UserPreferences.default_payload())
            self.db.add(prefs)
            self.db.flush()
        return prefs


_TOOL_HANDLERS: dict[str, Any] = {
    "get_user_preferences": MealAgent._tool_get_user_preferences,
    "get_recent_meal_history": MealAgent._tool_get_recent_meal_history,
    "lookup_product": MealAgent._tool_lookup_product,
    "upsert_product": MealAgent._tool_upsert_product,
    "calculate_nutrition": MealAgent._tool_calculate_nutrition,
    "save_meal_plan": MealAgent._tool_save_meal_plan,
}


# ── Helfer für Tool-Output ──────────────────────────────────────────────────


def _product_summary(p: Product) -> dict[str, Any]:
    return {
        "product_id": p.id,
        "name": p.name,
        "category": p.category,
        "kcal_per_100g": p.kcal_per_100g,
        "protein_g": p.protein_g,
        "carbs_g": p.carbs_g,
        "fat_g": p.fat_g,
        "typical_pack_size_g": p.typical_pack_size_g,
        "est_price_chf": float(p.est_price_chf) if p.est_price_chf is not None else None,
        "source": p.source,
    }


def _block_to_dict(block: Any) -> dict[str, Any]:
    """Wandelt einen SDK- oder Fake-Block in das dict-Format für Folge-Requests."""
    if isinstance(block, dict):
        return block
    if hasattr(block, "model_dump"):
        return dict(block.model_dump())
    btype = getattr(block, "type", None)
    base: dict[str, Any] = {"type": btype}
    if btype == "tool_use":
        base["id"] = block.id
        base["name"] = block.name
        base["input"] = block.input
    elif btype == "text":
        base["text"] = block.text
    return base


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Nicht serialisierbar: {type(value).__name__}")
