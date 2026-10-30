"""Add audit and metrics tracking fields

Revision ID: 003_audit_metrics
Revises: 002_enhanced
Create Date: 2026-10-30 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_audit_metrics"
down_revision: str | None = "002_enhanced"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("created_by", sa.String(length=100), nullable=True, server_default="system"))
    op.add_column("tasks", sa.Column("assigned_to", sa.String(length=100), nullable=True))
    op.add_column("tasks", sa.Column("estimated_hours", sa.Float(), nullable=True))
    op.add_column("tasks", sa.Column("actual_hours", sa.Float(), nullable=True))

    op.create_index(op.f("ix_tasks_assigned_to"), "tasks", ["assigned_to"], unique=False)
    op.create_index(op.f("ix_tasks_created_by"), "tasks", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tasks_created_by"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_assigned_to"), table_name="tasks")

    op.drop_column("tasks", "actual_hours")
    op.drop_column("tasks", "estimated_hours")
    op.drop_column("tasks", "assigned_to")
    op.drop_column("tasks", "created_by")
