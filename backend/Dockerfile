# Backend-Image — schlank, ARM64-kompatibel.
FROM python:3.11-slim

# Systempakete: build-essentials für C-Erweiterungen einiger Python-Pakete,
# tzdata für korrekte Zeitzonen im Scheduler.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential tzdata curl \
 && rm -rf /var/lib/apt/lists/*
# build-essential wird nur für die C-Erweiterungen beim pip-install gebraucht
# und danach entfernt, damit das Runtime-Image kein GCC enthält.

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Zurich

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get purge -y --auto-remove build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY . .

# Non-Root reduziert Blast-Radius bei RCE: ein Angreifer landet als
# unprivilegierter User, nicht als root im Container.
RUN useradd --system --uid 1000 --no-create-home appuser \
 && mkdir -p /data/db /data/logs \
 && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

# Beim Container-Start: erst Migration applien (idempotent), dann Server.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
