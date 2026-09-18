from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """D-035: agents/api.py's own ReviewDecision table, same physical SQLite file as
    proxy/db and frontend/db (via proxy.config.settings.database_url) but a separate
    Base/metadata, same reasoning as D-027. frontend/db/models.py's copy is kept in
    parallel during the Streamlit -> React migration window (D-034/D-035) — intentional
    duplication, not a mistake."""


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
