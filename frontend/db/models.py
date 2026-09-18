from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """D-027: kept separate from proxy/db/models.py's Base — a human's review decision
    is Fraud-Copilot application data, not SentinelAI proxy telemetry (D-001)."""


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    receipt_ref: Mapped[str] = mapped_column(String)
    system_verdict: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    hallucination_pct: Mapped[float] = mapped_column(Float)
    human_decision: Mapped[str] = mapped_column(String)
    reviewer_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
