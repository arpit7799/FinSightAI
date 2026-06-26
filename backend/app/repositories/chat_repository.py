# app/repositories/chat_repository.py
"""
Database operations for ChatSession and ChatMessage records.
"""

from sqlalchemy.orm import Session
from app.domain.models.chat import ChatSession, ChatMessage
from app.domain.models.enums import MessageRole


class ChatRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_session(self, filing_id: str, user_id: str, title: str = None) -> ChatSession:
        session = ChatSession(
            filing_id=filing_id,
            user_id=user_id,
            title=title,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        return self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

    def get_sessions_for_filing(self, filing_id: str, user_id: str) -> list[ChatSession]:
        return (
            self.db.query(ChatSession)
            .filter(
                ChatSession.filing_id == filing_id,
                ChatSession.user_id == user_id,
            )
            .order_by(ChatSession.updated_at.desc())
            .all()
        )

    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        citations: list = None,
        retrieved_chunks: list = None,
        llm_model: str = None,
        latency_ms: int = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations or [],
            retrieved_chunks=retrieved_chunks or [],
            llm_model=llm_model,
            latency_ms=latency_ms,
        )
        self.db.add(message)

        # Update session message count
        session = self.get_session(session_id)
        if session:
            session.message_count += 1

        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )