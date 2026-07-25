"""
SQLAlchemy-backed implementations of the repository interfaces. Each
method opens its own session_scope — short-lived, one-transaction-per-
call — rather than holding a session open across the object's lifetime.
Simpler to reason about and safe to share one repository instance
across the app.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from cogn_os.capture.types import WindowInfo
from cogn_os.storage.database import session_scope
from cogn_os.storage.models import AssistantCardRecord, EventRecord, SuggestionRecord
from cogn_os.storage.repository import (
    AssistantActionDTO,
    AssistantCardDTO,
    AssistantCardRepository,
    EventRepository,
    SuggestionRecordDTO,
    SuggestionRepository,
)

from cogn_os.screenshot.types import Screenshot
from cogn_os.storage.models import ScreenshotRecord
from cogn_os.storage.repository import ScreenshotRepository

from cogn_os.storage.models import FeatureLogRecord
from cogn_os.storage.repository import FeatureLogDTO, FeatureLogRepository


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


class SqlAlchemyAssistantCardRepository(AssistantCardRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, card: AssistantCardDTO) -> AssistantCardDTO:
        with session_scope(self._session_factory) as session:
            record = AssistantCardRecord(
                ts=card.ts,
                kind=card.kind,
                severity=card.severity,
                title=card.title,
                summary=card.summary,
                source=card.source,
                confidence=card.confidence,
                actions_json=json.dumps([asdict(a) for a in card.actions]),
                context_json=json.dumps(card.context),
                status=card.status,
            )
            session.add(record)
            session.flush()
            return self._to_dto(record)

    def recent(self, limit: int = 50, include_dismissed: bool = False) -> list[AssistantCardDTO]:
        with session_scope(self._session_factory) as session:
            stmt = select(AssistantCardRecord).order_by(AssistantCardRecord.id.desc()).limit(limit)
            if not include_dismissed:
                stmt = stmt.where(AssistantCardRecord.status != "dismissed")
            return [self._to_dto(r) for r in session.scalars(stmt)]

    def set_status(self, card_id: int, status: str) -> bool:
        with session_scope(self._session_factory) as session:
            record = session.get(AssistantCardRecord, card_id)
            if record is None:
                return False
            record.status = status
            return True

    def _to_dto(self, r: AssistantCardRecord) -> AssistantCardDTO:
        actions = [AssistantActionDTO(**item) for item in json.loads(r.actions_json)]
        return AssistantCardDTO(
            id=r.id,
            ts=r.ts,
            kind=r.kind,
            severity=r.severity,
            title=r.title,
            summary=r.summary,
            source=r.source,
            confidence=r.confidence,
            actions=actions,
            context=json.loads(r.context_json),
            status=r.status,
        )


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
        
class SqlAlchemyFeatureLogRepository(FeatureLogRepository):
    _FEATURE_FIELDS = (
        "seconds_since_last_llm_call", "hour_of_day", "is_weekend", "app_category",
        "title_length", "app_changed", "is_first_time_app_today", "switches_last_5min",
    )

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, info: WindowInfo, features: dict, probability: float, flagged: bool) -> int:
        with session_scope(self._session_factory) as session:
            record = FeatureLogRecord(
                ts=info.captured_at,
                app_name=info.app_name,
                window_title=info.window_title,
                predicted_probability=probability,
                model_flagged=flagged,
                **{k: features[k] for k in self._FEATURE_FIELDS},
            )
            session.add(record)
            session.flush()
            return record.id

    def set_label(self, log_id: int, label: int) -> bool:
        with session_scope(self._session_factory) as session:
            record = session.get(FeatureLogRecord, log_id)
            if record is None:
                return False
            record.user_label = label
            return True

    def recent_unlabeled(self, limit: int = 10) -> list[FeatureLogDTO]:
        with session_scope(self._session_factory) as session:
            stmt = (
                select(FeatureLogRecord)
                .where(FeatureLogRecord.user_label.is_(None))
                .order_by(FeatureLogRecord.id.desc())
                .limit(limit)
            )
            return [self._to_dto(r) for r in session.scalars(stmt)]

    def labeled_examples(self) -> list[FeatureLogDTO]:
        with session_scope(self._session_factory) as session:
            stmt = select(FeatureLogRecord).where(FeatureLogRecord.user_label.is_not(None))
            return [self._to_dto(r) for r in session.scalars(stmt)]

    def _to_dto(self, r: FeatureLogRecord) -> FeatureLogDTO:
        return FeatureLogDTO(
            id=r.id, ts=r.ts, app_name=r.app_name, window_title=r.window_title,
            features={k: getattr(r, k) for k in self._FEATURE_FIELDS},
            predicted_probability=r.predicted_probability,
            model_flagged=r.model_flagged, user_label=r.user_label,
        )
