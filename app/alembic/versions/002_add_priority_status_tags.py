"""Add priority, status, due_date, tags and soft delete

Revision ID: 002_enhanced
Revises: 001_initial
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_enhanced"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"))
    op.add_column("tasks", sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"))
    op.add_column("tasks", sa.Column("due_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("tags", sa.String(length=500), nullable=True, server_default=""))
    op.add_column("tasks", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("tasks", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)
    op.create_index(op.f("ix_tasks_priority"), "tasks", ["priority"], unique=False)
    op.create_index(op.f("ix_tasks_completed"), "tasks", ["completed"], unique=False)
    op.create_index(op.f("ix_tasks_is_deleted"), "tasks", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tasks_is_deleted"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_completed"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_priority"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")

    op.drop_column("tasks", "deleted_at")
    op.drop_column("tasks", "is_deleted")
    op.drop_column("tasks", "tags")
    op.drop_column("tasks", "due_date")
    op.drop_column("tasks", "priority")
    op.drop_column("tasks", "status")
