"""Create Phase 2 core workspace tables and enable pgvector.

Revision ID: 20261024_0001
Revises: None
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261024_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

workspace_role = sa.Enum("OWNER", "ADMIN", "MEMBER", "VIEWER", name="workspace_role")
project_status = sa.Enum("ACTIVE", "ON_HOLD", "COMPLETED", "ARCHIVED", name="project_status")
task_status = sa.Enum("TODO", "IN_PROGRESS", "BLOCKED", "DONE", name="task_status")
task_priority = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="task_priority")


def uuid_column(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.Uuid(as_uuid=True), nullable=nullable)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        uuid_column("id"),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "workspaces",
        uuid_column("id"),
        sa.Column("name", sa.String(120), nullable=False),
        *timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_deleted_at", "workspaces", ["deleted_at"])

    op.create_table(
        "workspace_members",
        uuid_column("id"),
        uuid_column("workspace_id"),
        uuid_column("user_id"),
        sa.Column("role", workspace_role, nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    op.create_table(
        "projects",
        uuid_column("id"),
        uuid_column("workspace_id"),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", project_status, nullable=False),
        uuid_column("created_by"),
        *timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"])

    op.create_table(
        "tasks",
        uuid_column("id"),
        uuid_column("workspace_id"),
        uuid_column("project_id"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.Column("priority", task_priority, nullable=False),
        uuid_column("assignee_id", nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        uuid_column("created_by"),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("workspace_id", "project_id", "assignee_id", "status", "due_date", "deleted_at"):
        op.create_index(f"ix_tasks_{column}", "tasks", [column])

    op.create_table(
        "task_dependencies",
        uuid_column("id"),
        uuid_column("workspace_id"),
        uuid_column("task_id"),
        uuid_column("depends_on_task_id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
        sa.CheckConstraint("task_id != depends_on_task_id", name="ck_no_self_dependency"),
    )
    for column in ("workspace_id", "task_id", "depends_on_task_id"):
        op.create_index(f"ix_task_dependencies_{column}", "task_dependencies", [column])

    op.create_table(
        "refresh_tokens",
        uuid_column("id"),
        uuid_column("user_id"),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        uuid_column("replaced_by_id", nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "audit_logs",
        uuid_column("id"),
        uuid_column("workspace_id", nullable=True),
        uuid_column("user_id", nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        uuid_column("entity_id", nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_workspace_id", "audit_logs", ["workspace_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_workspace_created", "audit_logs", ["workspace_id", "created_at"])


def downgrade() -> None:
    for table in (
        "audit_logs",
        "refresh_tokens",
        "task_dependencies",
        "tasks",
        "projects",
        "workspace_members",
        "workspaces",
        "users",
    ):
        op.drop_table(table)
    for enum in (task_priority, task_status, project_status, workspace_role):
        enum.drop(op.get_bind(), checkfirst=True)
