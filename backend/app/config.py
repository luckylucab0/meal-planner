"""Pydantic-Settings — liest Konfiguration aus Environment-Variablen / `.env`.

Wird in Schritt 2 (Backend-Foundation) ausgebaut.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Globale Anwendungs-Einstellungen.

    Werte stammen aus Environment-Variablen; Defaults sind so gewählt, dass
    sie in der Docker-Compose-Umgebung sinnvoll sind.
    """

    anthropic_api_key: str = ""
    database_url: str = "sqlite:////data/db/meal_planner.db"
    encryption_key: str = ""
    log_level: str = "INFO"
    off_user_agent: str = "MealPlanner/0.1 (selfhosted)"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
