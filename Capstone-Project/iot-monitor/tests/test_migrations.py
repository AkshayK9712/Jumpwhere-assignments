"""Run the real Alembic migration on a temporary SQLite file."""
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app import models  # noqa: F401
from app.db.session import Base

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = {"users", "user_profiles", "refresh_tokens", "sensors",
            "sensor_readings", "activity_logs", "reports", "system_config"}


def _config(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", (ROOT / "db" / "migrations").as_posix())
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_creates_all_tables_and_downgrade_removes_them(tmp_path):
    url = f"sqlite:///{(tmp_path / 'mig.db').as_posix()}"
    cfg = _config(url)

    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert EXPECTED <= tables

    command.downgrade(cfg, "base")
    assert not (EXPECTED & set(inspect(create_engine(url)).get_table_names()))


def test_migration_matches_models(tmp_path):
    """If this fails, a model changed without a new migration."""
    url = f"sqlite:///{(tmp_path / 'drift.db').as_posix()}"
    command.upgrade(_config(url), "head")

    engine = create_engine(url)
    with engine.connect() as conn:
        diffs = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": False}), Base.metadata)

    structural = [d for d in diffs
                  if isinstance(d, tuple) and d[0] in {"add_table", "remove_table", "add_column", "remove_column"}
                  and not (d[0] == "remove_table" and d[1].name == "alembic_version")]
    assert structural == []
