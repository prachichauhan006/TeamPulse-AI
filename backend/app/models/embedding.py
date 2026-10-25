import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.types import Vector1536
from app.models.enums import EmbeddingSourceType


class Embedding(Base, TimestampMixin):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "chunk_index", name="uq_embedding_source_chunk"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    source_type: Mapped[EmbeddingSourceType] = mapped_column(
        Enum(EmbeddingSourceType, name="embedding_source_type"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector1536(), nullable=False)
