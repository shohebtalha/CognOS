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
from cogn_os.storage.models import EventRecord, SuggestionRecord
from cogn_os.storage.repository import EventRepository, SuggestionRecordDTO, SuggestionRepository

from cogn_os.screenshot.types import Screenshot
from cogn_os.storage.models import ScreenshotRecord
from cogn_os.storage.repository import ScreenshotRepository


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
            records.reverse()
            return [
                WindowInfo(app_name=r.app_name, window_title=r.window_title, captured_at=r.ts)
                for r in records
            ]

    def count(self) -> int:
        with session_scope(self._session_factory) as session:
            stmt = select(EventRecord)
            return len(list(session.scalars(stmt)))


class SqlAlchemySuggestionRepository(SuggestionRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, info: WindowInfo, suggestion: str) -> SuggestionRecordDTO:
        with session_scope(self._session_factory) as session:
            record = SuggestionRecord(
                ts=info.captured_at,
                app_name=info.app_name,
                window_title=info.window_title,
                suggestion=suggestion,
            )
            session.add(record)
            session.flush()
            return SuggestionRecordDTO(
                id=record.id,
                ts=record.ts,
                app_name=record.app_name,
                window_title=record.window_title,
                suggestion=record.suggestion,
            )

    def recent(self, limit: int = 20) -> list[SuggestionRecordDTO]:
        with session_scope(self._session_factory) as session:
            stmt = select(SuggestionRecord).order_by(SuggestionRecord.id.desc()).limit(limit)
            records = list(session.scalars(stmt))
            return [
                SuggestionRecordDTO(
                    id=r.id, ts=r.ts, app_name=r.app_name,
                    window_title=r.window_title, suggestion=r.suggestion,
                )
                for r in records
            ]


class SqlAlchemyScreenshotRepository(ScreenshotRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, screenshot: Screenshot, event_id: int | None = None) -> int:
        with session_scope(self._session_factory) as session:
            record = ScreenshotRecord(
                ts=screenshot.captured_at,
                event_id=event_id,
                image_b64=screenshot.image_b64,
                width=screenshot.width,
                height=screenshot.height,
                format=screenshot.format,
            )
            session.add(record)
            session.flush()
            return record.id

    def count(self) -> int:
        with session_scope(self._session_factory) as session:
            stmt = select(ScreenshotRecord)
            return len(list(session.scalars(stmt)))