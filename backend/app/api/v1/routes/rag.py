# app/api/v1/routes/rag.py
"""
API routes for the RAG system.

Endpoints:
    POST /rag/{filing_id}/embed       - Run embedding pipeline
    POST /rag/{filing_id}/ask         - Ask a question about a filing
    GET  /rag/sessions/{session_id}   - Get chat history
    GET  /rag/{filing_id}/sessions    - List sessions for a filing
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.services.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])


# ── Request schemas ───────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    session_id: str | None = None  # pass to continue a conversation


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/{filing_id}/embed")
def embed_filing(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """
    Run the embedding pipeline for a filing.
    Chunks the document, generates BGE embeddings, stores in Qdrant.
    Must be run before /ask will work.
    """
    service = RAGService(db)
    return service.embed_filing(filing_id)


@router.post("/{filing_id}/ask")
def ask_question(
    filing_id: str,
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Ask a natural language question about a filing.

    Example questions:
        - "What are the major risks mentioned?"
        - "Why did revenue decline?"
        - "Summarize the management discussion section."
        - "What is the company's debt situation?"

    Returns an answer grounded in the document with citations.
    """
    service = RAGService(db)
    return service.ask(
        filing_id=filing_id,
        question=payload.question,
        session_id=payload.session_id,
        user_id=str(current_user.id),
    )


@router.get("/sessions/{session_id}/history")
def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the full conversation history for a chat session."""
    service = RAGService(db)
    return {"session_id": session_id, "messages": service.get_history(session_id)}


@router.get("/{filing_id}/sessions")
def list_sessions(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all chat sessions for a filing by the current user."""
    from app.repositories.chat_repository import ChatRepository
    sessions = ChatRepository(db).get_sessions_for_filing(
        filing_id, str(current_user.id)
    )
    return [
        {
            "session_id": str(s.id),
            "title": s.title,
            "message_count": s.message_count,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]