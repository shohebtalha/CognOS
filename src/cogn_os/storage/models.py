"""
SQLAlchemy ORM models. Two tables, mirroring the two things the system
records: raw window-change events (the timeline) and LLM-generated
suggestions (a subset of events that were interesting enough to surface).
Kept separate from the domain dataclasses in capture/types.py — ORM
models describe *storage shape*, not business logic, and the mapping
between them lives in the repository layer, not here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EventRecord(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    window_title: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"EventRecord(id={self.id}, app_name={self.app_name!r}, ts={self.ts})"


class SuggestionRecord(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    window_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"SuggestionRecord(id={self.id}, suggestion={self.suggestion!r})"
    
class ScreenshotRecord(Base):
    __tablename__ = "screenshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    image_b64: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="jpeg")

    def __repr__(self) -> str:
        return f"ScreenshotRecord(id={self.id}, ts={self.ts}, {self.width}x{self.height})"
    
class FeatureLogRecord(Base):
    __tablename__ = "feature_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    window_title: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # feature values, stored flat rather than as JSON, so retraining can
    # load this table directly into a DataFrame with pandas.read_sql
    # without a JSON-parsing step — same rationale as EventRecord.
    seconds_since_last_llm_call: Mapped[float] = mapped_column(nullable=False)
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    is_weekend: Mapped[bool] = mapped_column(nullable=False)
    app_category: Mapped[str] = mapped_column(String(32), nullable=False)
    title_length: Mapped[int] = mapped_column(Integer, nullable=False)
    app_changed: Mapped[bool] = mapped_column(nullable=False)
    is_first_time_app_today: Mapped[bool] = mapped_column(nullable=False)
    switches_last_5min: Mapped[int] = mapped_column(Integer, nullable=False)

    # model's own decision at the time, logged for transparency/debugging
    predicted_probability: Mapped[float] = mapped_column(nullable=False)
    model_flagged: Mapped[bool] = mapped_column(nullable=False)

    # feedback label: NULL until the user explicitly labels it via
    # 'cognos feedback' (Commit #5). Only labeled rows are usable for
    # supervised retraining — unlabeled rows are logged for volume/
    # future labeling but excluded from training until then.
    user_label: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"FeatureLogRecord(id={self.id}, app={self.app_name}, label={self.user_label})"