# Backend-Image — schlank, ARM64-kompatibel.
FROM python:3.11-slim

# Systempakete: build-essentials für C-Erweiterungen einiger Python-Pakete,
# tzdata für korrekte Zeitzonen im Scheduler.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential tzdata curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Zurich

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Beim Container-Start: erst Migration applien (idempotent), dann Server.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
