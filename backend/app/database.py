"""SQLAlchemy-Setup — Engine, Session-Factory, Declarative Base.

Wird in Schritt 2/3 vollständig implementiert.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Gemeinsame Basis-Klasse für alle ORM-Modelle."""
