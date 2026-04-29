"""FastAPI-Einstiegspunkt.

Initialisiert Logging, registriert Exception-Handler für Domain-Fehler und
exponiert einen Health-Endpoint. Router (preferences, plans, products, …)
werden in den nachfolgenden Implementierungs-Schritten registriert.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import calendar as calendar_api
from app.api import plans as plans_api
from app.api import preferences as preferences_api
from app.api import products as products_api
from app.api import settings as settings_api
from app.api import shopping_list as shopping_list_api
from app.api import stats as stats_api
from app.config import settings
from app.exceptions import MealPlannerError
from app.logging_setup import setup_logging
from app.rate_limit import limiter
from app.scheduler import make_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """App-Lifecycle — Logging + Scheduler beim Start, sauberes Shutdown am Ende."""
    setup_logging()
    logger.info("Meal Planner Backend startet (db={})", settings.database_url)
    scheduler = make_scheduler()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Meal Planner Backend wird beendet.")


app = FastAPI(title="Meal Planner", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(MealPlannerError)
async def domain_error_handler(_request: Request, exc: MealPlannerError) -> JSONResponse:
    """Wandelt Domain-Exceptions in saubere 4xx/5xx-Antworten."""
    logger.warning("Domain-Fehler: {}", exc)
    return JSONResponse(
        status_code=400,
        content={"error": exc.__class__.__name__, "detail": str(exc)},
    )


app.include_router(preferences_api.router)
app.include_router(products_api.router)
app.include_router(plans_api.router)
app.include_router(shopping_list_api.router)
app.include_router(stats_api.router)
app.include_router(calendar_api.router)
app.include_router(settings_api.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness-Check für Docker und Frontend-Statusbanner."""
    return {"status": "ok"}
