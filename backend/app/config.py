"""Pydantic-Settings — liest Konfiguration aus Environment-Variablen / `.env`.

Wird zur App-Startzeit einmal instanziiert (`settings`-Singleton). Alle
Module beziehen Konfig ausschliesslich darüber, niemals direkt aus `os.environ`.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Globale Anwendungs-Einstellungen.

    Werte stammen aus Environment-Variablen; Defaults sind so gewählt, dass
    sie in der Docker-Compose-Umgebung sinnvoll sind.
    """

    # Anthropic
    anthropic_api_key: str = Field(default="", description="Claude-API-Key")
    model_planner: str = "claude-opus-4-7"
    model_helper: str = "claude-haiku-4-5-20251001"

    # Datenbank
    database_url: str = "sqlite:////data/db/meal_planner.db"

    # Crypto (CalDAV-Credentials)
    encryption_key: str = ""

    # Logging
    log_level: str = "INFO"
    log_dir: Path = Path("/data/logs")

    # Open Food Facts
    off_user_agent: str = "MealPlanner/0.1 (selfhosted)"
    off_base_url: str = "https://world.openfoodfacts.org"

    # Zeitzone (für Scheduler & ICS-Export)
    timezone: str = "Europe/Zurich"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached Singleton — Settings werden einmal pro Prozess geladen."""
    return Settings()


settings = get_settings()
