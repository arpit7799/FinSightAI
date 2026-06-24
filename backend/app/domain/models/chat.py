# app/domain/models/chat.py
"""
Chat models — RAG Q&A conversation history.
ChatSession groups messages; ChatMessage stores each turn
with full citation and retrieval metadata.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import MessageRole
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing
    from app.domain.models.user import User


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A conversation session between a user and the RAG system
    about a specific filing.

    One session = one document = one conversation thread.
    Multiple sessions per filing are allowed (e.g., different analysts).
    The title is auto-generated from the first user message.
    """
    __tablename__ = "chat_sessions"

    # ── References ────────────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Session metadata ──────────────────────────────────────────────────
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship(
        "Filing", back_populates="chat_sessions"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="chat_sessions"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    # ── Indexes ───────────────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_chat_sessions_filing", "filing_id"),
        Index("idx_chat_sessions_user", "user_id"),
        Index("idx_chat_sessions_updated", "updated_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ChatSession id={self.id} filing_id={self.filing_id} "
            f"user_id={self.user_id} messages={self.message_count}>"
        )


class ChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single message turn in a RAG conversation.

    For USER messages: content is the user's question.
    For ASSISTANT messages: content is Llama 3's answer,
      with citations linking back to DocumentChunk records
      and full retrieval metadata stored for debugging.

    JSONB schema for citations:
        [{"chunk_id": "uuid", "chunk_text": "...",
          "page": 23, "section": "RISK_FACTORS",
          "score": 0.89}, ...]

    JSONB schema for retrieved_chunks:
        Full Qdrant retrieval payload — kept for RAG pipeline debugging.

    JSONB schema for retrieval_scores:
        [{"chunk_id": "uuid", "dense_score": 0.91,
          "sparse_score": 0.72, "rrf_score": 0.85}, ...]
    """
    __tablename__ = "chat_messages"

    # ── Session reference ─────────────────────────────────────────────────
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Message content ───────────────────────────────────────────────────
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", create_type=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ── RAG metadata (ASSISTANT messages only) ────────────────────────────
    citations: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    retrieved_chunks: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    retrieval_scores: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    # ── LLM metadata ─────────────────────────────────────────────────────
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )

    # ── Indexes ───────────────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_messages_session", "session_id", "created_at"),
        Index("idx_messages_role", "session_id", "role"),
    )

    def __repr__(self) -> str:
        return (
            f"<ChatMessage id={self.id} session_id={self.session_id} "
            f"role={self.role}>"
        )
