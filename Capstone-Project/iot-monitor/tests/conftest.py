import sys
from pathlib import Path

import pytest

# Make `app` importable even if pytest.ini is not picked up
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture()
def engine():
    """One in-memory SQLite database per test, shared by all sessions."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from app import models  # noqa: F401
    from app.db.session import Base

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(engine):
    """FastAPI test client wired to the in-memory database."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.db.session import get_db
    from app.main import app

    TestingSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
