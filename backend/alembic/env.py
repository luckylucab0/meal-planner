"""Alembic-Environment.

In Schritt 3 vollständig konfiguriert; aktuell Platzhalter, damit `alembic init`
nicht erneut ausgeführt werden muss.
"""

from logging.config import fileConfig

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    """Offline-Modus — wird in Schritt 3 implementiert."""
    raise NotImplementedError("Alembic-Offline-Mode noch nicht konfiguriert.")


def run_migrations_online() -> None:
    """Online-Modus — wird in Schritt 3 implementiert."""
    raise NotImplementedError("Alembic-Online-Mode noch nicht konfiguriert.")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
