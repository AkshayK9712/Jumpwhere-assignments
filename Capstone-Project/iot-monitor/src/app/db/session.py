from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# SQLite (handy for local dev without Docker) needs this flag for use across threads.
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# pool_pre_ping avoids stale connections; the engine connects lazily.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record):
        # SQLite ignores foreign keys (and ON DELETE CASCADE) unless this is switched on.
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
