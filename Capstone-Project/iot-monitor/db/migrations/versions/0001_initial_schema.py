"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# JSONB on PostgreSQL, plain JSON elsewhere (SQLite for local dev/tests)
JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
# BigInteger PKs that still autoincrement on SQLite
BigIntPK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _ts(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("role", sa.Enum("admin", "user", "guest", name="userrole", native_enum=False, length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("bio", sa.String(500)),
        sa.Column("phone", sa.String(30)),
        sa.Column("preferences", JSONType, nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "sensors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.Enum("active", "inactive", "faulty", name="sensorstatus", native_enum=False, length=20), nullable=False),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="priority", native_enum=False, length=20), nullable=False),
        sa.Column(
            "category",
            sa.Enum("temperature", "pressure", "humidity", "vibration", "flow", "other",
                    name="sensorcategory", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("metadata", JSONType, nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_sensors_user_id", "sensors", ["user_id"])
    op.create_index("ix_sensors_status", "sensors", ["status"])
    op.create_index("ix_sensors_category", "sensors", ["category"])

    op.create_table(
        "sensor_readings",
        sa.Column("id", BigIntPK, primary_key=True),
        sa.Column("sensor_id", sa.Integer(), sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_readings_sensor_time", "sensor_readings", ["sensor_id", "recorded_at"])

    op.create_table(
        "activity_logs",
        sa.Column("id", BigIntPK, primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50)),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("details", JSONType, nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(255)),
        _ts("created_at"),
    )
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_index("ix_activity_entity", "activity_logs", ["entity_type", "entity_id"])
    op.create_index("ix_activity_created", "activity_logs", ["created_at"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("query_params", JSONType, nullable=False),
        sa.Column("format", sa.Enum("pdf", "csv", name="reportformat", native_enum=False, length=10), nullable=False),
        sa.Column("status", sa.Enum("pending", "ready", "failed", name="reportstatus", native_enum=False, length=10), nullable=False),
        sa.Column("scheduled", sa.Boolean(), nullable=False),
        sa.Column("file_path", sa.String(500)),
        _ts("created_at"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])

    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", JSONType, nullable=True),
        sa.Column("description", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        _ts("updated_at"),
    )
    op.create_index("ix_system_config_key", "system_config", ["key"], unique=True)


def downgrade() -> None:
    for table in ("system_config", "reports", "activity_logs", "sensor_readings",
                  "sensors", "refresh_tokens", "user_profiles", "users"):
        op.drop_table(table)
