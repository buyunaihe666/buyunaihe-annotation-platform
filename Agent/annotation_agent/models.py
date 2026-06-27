from datetime import datetime
from typing import Any, Optional

from sqlalchemy import String, Text, DECIMAL, DateTime, BigInteger, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    task_item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    labeler_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    suggestion: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AIAuditReport(Base):
    __tablename__ = "ai_audit_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    task_item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    score: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 2), nullable=True)
    issues: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)