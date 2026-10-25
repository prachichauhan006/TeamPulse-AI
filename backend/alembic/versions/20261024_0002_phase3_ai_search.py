"""Add approval-gated AI, notes, documents, and vector search.

Revision ID: 20261024_0002
Revises: 20261024_0001
"""
from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261024_0002"
down_revision: str | None = "20261024_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

embedding_status = sa.Enum("PENDING", "PROCESSING", "COMPLETE", "FAILED", "SKIPPED", name="embedding_status")
embedding_status_existing = sa.Enum(
    "PENDING", "PROCESSING", "COMPLETE", "FAILED", "SKIPPED", name="embedding_status", create_type=False
)
ai_proposal_type = sa.Enum("PROJECT_PLAN", "MEETING_ACTIONS", name="ai_proposal_type")
ai_proposal_status = sa.Enum("PENDING", "APPROVED", "REJECTED", name="ai_proposal_status")
embedding_source_type = sa.Enum("DOCUMENT", "MEETING_NOTE", name="embedding_source_type")


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
        "meeting_notes",
        uuid_column("id"),
        uuid_column("workspace_id"),
        uuid_column("project_id", nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        uuid_column("created_by"),
        sa.Column("embedding_status", embedding_status, nullable=False),
        sa.Column("embedding_error", sa.String(500), nullable=True),
        *timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("workspace_id", "project_id", "deleted_at"):
        op.create_index(f"ix_meeting_notes_{column}", "meeting_notes", [column])

    op.create_table(
        "documents",
        uuid_column("id"),
        uuid_column("workspace_id"),
        uuid_column("project_id", nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        uuid_column("created_by"),
        sa.Column("embedding_status", embedding_status_existing, nullable=False),
        sa.Column("embedding_error", sa.String(500), nullable=True),
        *timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("workspace_id", "project_id", "deleted_at"):
        op.create_index(f"ix_documents_{column}", "documents", [column])

    op.create_table(
        "ai_proposals",
        uuid_column("id"),
        uuid_column("workspace_id"),
        sa.Column("proposal_type", ai_proposal_type, nullable=False),
        sa.Column("status", ai_proposal_status, nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        uuid_column("meeting_note_id", nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        uuid_column("created_by"),
        uuid_column("reviewed_by", nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["meeting_note_id"], ["meeting_notes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("workspace_id", "proposal_type", "status", "meeting_note_id"):
        op.create_index(f"ix_ai_proposals_{column}", "ai_proposals", [column])

    op.create_table(
        "embeddings",
        uuid_column("id"),
        uuid_column("workspace_id"),
        sa.Column("source_type", embedding_source_type, nullable=False),
        uuid_column("source_id"),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content_snippet", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", "chunk_index", name="uq_embedding_source_chunk"),
    )
    for column in ("workspace_id", "source_type", "source_id"):
        op.create_index(f"ix_embeddings_{column}", "embeddings", [column])
    op.execute(
        "CREATE INDEX ix_embeddings_embedding_hnsw "
        "ON embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    for table in ("embeddings", "ai_proposals", "documents", "meeting_notes"):
        op.drop_table(table)
    for enum in (embedding_source_type, ai_proposal_status, ai_proposal_type, embedding_status):
        enum.drop(op.get_bind(), checkfirst=True)
