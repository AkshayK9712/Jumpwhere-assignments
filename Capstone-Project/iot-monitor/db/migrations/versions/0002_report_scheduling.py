"""report scheduling columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # batch mode lets the same migration run on PostgreSQL and SQLite
    with op.batch_alter_table("reports") as batch:
        batch.add_column(sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("source_id", sa.Integer(), nullable=True))
        batch.create_index("ix_reports_next_run_at", ["next_run_at"])


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.drop_index("ix_reports_next_run_at")
        batch.drop_column("source_id")
        batch.drop_column("last_run_at")
        batch.drop_column("next_run_at")
