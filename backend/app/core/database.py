# app/core/database.py
"""
SQLAlchemy engine, session factory, and declarative base.
All models inherit from Base defined here.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from typing import Generator

from app.core.config import settings


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base.
    All ORM models must inherit from this class.
    """
    pass


# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # Verify connections before use (handles stale connections)
    echo=settings.DEBUG,  # Log all SQL in development; set DEBUG=False in prod
)


# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── FastAPI Dependency ────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    Automatically closes the session after the request completes.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
