import itertools
import sys
from pathlib import Path

import pytest

# Make `app` importable even if pytest.ini is not picked up
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch):
    """Every test: no rate limiting, emails kept in memory, clean state."""
    from app.core.config import settings
    from app.core.rate_limit import limiter
    from app.services import email

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "memory")
    limiter.reset()
    email.OUTBOX.clear()


@pytest.fixture()
def engine():
    """One in-memory SQLite database per test, shared by all sessions."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    from app import models  # noqa: F401
    from app.db.session import Base

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

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


@pytest.fixture()
def make_user(db_session):
    """Create a ready-to-use user directly in the database (no HTTP, no slow hashing)."""
    counter = itertools.count(1)

    def _make(role="user", email=None, is_active=True, verified=True, name="Test User"):
        from app.models import User, UserProfile, UserRole

        user = User(
            email=email or f"{role}{next(counter)}@example.com",
            password_hash="x",
            name=name,
            role=UserRole(role),
            is_active=is_active,
            email_verified=verified,
        )
        user.profile = UserProfile()
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def bearer():
    """bearer(user) -> {"Authorization": "Bearer <jwt>"}"""
    from app.core.security import create_access_token

    def _headers(user):
        return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}

    return _headers
