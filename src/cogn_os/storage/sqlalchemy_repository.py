"""
SQLAlchemy-backed implementations of the repository interfaces. Each
method opens its own session_scope — short-lived, one-transaction-per-
call — rather than holding a session open across the object's lifetime.
Simpler to reason about and safe to share one repository instance
across the app.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from cogn_os.capture.types import WindowInfo
from cogn_os.storage.database import session_scope
from cogn_os.storage.models import EventRecord
from cogn_os.storage.repository import EventRepository


class SqlAlchemyEventRepository(EventRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, info: WindowInfo) -> None:
        with session_scope(self._session_factory) as session:
            record = EventRecord(
                ts=info.captured_at,
                app_name=info.app_name,
                window_title=info.window_title,
            )
            session.add(record)

    def recent(self, limit: int = 8) -> list[WindowInfo]:
        with session_scope(self._session_factory) as session:
            stmt = select(EventRecord).order_by(EventRecord.id.desc()).limit(limit)
            records = list(session.scalars(stmt))
            records.reverse()  # chronological order for the caller
            return [
                WindowInfo(app_name=r.app_name, window_title=r.window_title, captured_at=r.ts)
                for r in records
            ]

    def count(self) -> int:
        with session_scope(self._session_factory) as session:
            stmt = select(EventRecord)
            return len(list(session.scalars(stmt)))