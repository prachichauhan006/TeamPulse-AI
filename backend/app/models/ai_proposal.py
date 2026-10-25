import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import AIProposalStatus, AIProposalType


class AIProposal(Base, TimestampMixin):
    __tablename__ = "ai_proposals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    proposal_type: Mapped[AIProposalType] = mapped_column(
        Enum(AIProposalType, name="ai_proposal_type"), nullable=False, index=True
    )
    status: Mapped[AIProposalStatus] = mapped_column(
        Enum(AIProposalStatus, name="ai_proposal_status"), default=AIProposalStatus.PENDING, nullable=False, index=True
    )
    source_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    meeting_note_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("meeting_notes.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column("result", JSON, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
