"""FastAPI-Einstiegspunkt.

Bündelt alle Router unter `/api` und stellt einen Health-Endpoint bereit.
Echte Implementierung folgt schrittweise (siehe Plan).
"""

from fastapi import FastAPI

app = FastAPI(title="Meal Planner", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness-Check für Docker und Frontend-Statusbanner."""
    return {"status": "ok"}
