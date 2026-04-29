"""SQLAlchemy-Setup — Engine, Session-Factory, FastAPI-Dependency, Declarative Base.

SQLite läuft in einem Container, daher `check_same_thread=False`. Für die Tests
wird die Engine in `tests/conftest.py` per Override durch eine In-Memory-Variante
ersetzt.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Gemeinsame Basis-Klasse für alle ORM-Modelle."""


def _make_engine(url: str) -> Engine:
    """Erzeugt eine Engine mit den korrekten Connect-Args für SQLite."""
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, future=True)


engine: Engine = _make_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI-Dependency — gibt eine Session pro Request frei."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
