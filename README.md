# Meal Planner

Selbst-gehosteter AI-Meal-Planning-Agent für den Raspberry Pi (ARM64). Erstellt
wöchentliche Mittag- und Abendessen-Pläne basierend auf persönlichen Vorlieben
und Fitness-Zielen — inklusive Makro-Tracking, Einkaufsliste und Kalender-Export.

> **Status:** Skeleton-Phase. Funktionalität wird inkrementell umgesetzt
> (siehe [`.claude/plans/projekt-meal-planner-transient-otter.md`](.claude/plans/projekt-meal-planner-transient-otter.md)).

## Stack

- **Backend:** Python 3.11 · FastAPI · SQLAlchemy · SQLite · APScheduler
- **AI:** Anthropic Claude (`claude-opus-4-7` für Planung, `claude-haiku-4-5-20251001` für Sub-Tasks)
- **Nährwert-Daten:** Open Food Facts API (mit lokalem Cache)
- **Frontend:** React 18 · Vite · TailwindCSS · shadcn/ui · Recharts
- **Container:** Docker Compose (ARM64)

## Schnellstart

```bash
cp .env.example .env
# .env mit ANTHROPIC_API_KEY und ENCRYPTION_KEY befüllen
docker compose up -d
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## Roadmap

Implementierungs-Reihenfolge siehe Plan-Datei. Nach dem Skeleton folgen:
DB-Modelle → Preferences → OFF-Service → Meal-Agent → Wochenplan → Einkaufsliste →
Makros → ICS-Export → CalDAV → Scheduler → Polishing.
