"""Pytest-Fixtures.

Pro Test wird eine frische In-Memory-SQLite-DB aufgebaut und die
`get_db`-Dependency durch eine Session gegen diese DB überschrieben.
Damit sind Tests deterministisch und ohne Plattenzugriff schnell.

Rate-Limit: slowapi speichert Counters in einem In-Memory-Storage, das
über Tests hinweg akkumuliert. Um Flakiness durch 429-Antworten zu
vermeiden, wird `limiter.enabled = False` vor dem Client gesetzt und
danach wieder aktiviert. Das ist die offiziell empfohlene Methode aus
den slowapi-Docs (kein Reset-API in 0.1.x vorhanden).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.rate_limit import limiter


@pytest.fixture
def client() -> Iterator[TestClient]:
    """TestClient mit überschriebener DB und deaktiviertem Rate-Limit."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def _override_get_db() -> Iterator[Session]:
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    limiter.enabled = False
    try:
        with TestClient(app) as c:
            yield c
    finally:
        limiter.enabled = True
        app.dependency_overrides.clear()
        engine.dispose()
