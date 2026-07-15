"""
Repository interfaces, expressed in terms of domain types (WindowInfo),
not ORM models. Callers elsewhere in the app (the capture loop, the API)
depend on these interfaces, never on SQLAlchemy directly — same pattern
as WindowInfoSource in the capture package. This is what lets us swap
SQLite for Postgres later, or use an in-memory fake in tests, without
touching calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from cogn_os.capture.types import WindowInfo

from cogn_os.screenshot.types import Screenshot


@dataclass(frozen=True, slots=True)
class SuggestionRecordDTO:
    """A suggestion as read back from storage, including its id/timestamp."""

    id: int
    ts: datetime
    app_name: str
    window_title: str
    suggestion: str


class EventRepository(ABC):
    @abstractmethod
    def add(self, info: WindowInfo) -> None:
        """Persist a single window-change event."""
        raise NotImplementedError

    @abstractmethod
    def recent(self, limit: int = 8) -> list[WindowInfo]:
        """Return the most recent events, oldest first (chronological)."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError


class SuggestionRepository(ABC):
    @abstractmethod
    def add(self, info: WindowInfo, suggestion: str) -> SuggestionRecordDTO:
        """Persist a suggestion and return it with its assigned id/ts."""
        raise NotImplementedError

    @abstractmethod
    def recent(self, limit: int = 20) -> list[SuggestionRecordDTO]:
        """Return the most recent suggestions, newest first."""
        raise NotImplementedError
    
class ScreenshotRepository(ABC):
    @abstractmethod
    def add(self, screenshot: "Screenshot", event_id: int | None = None) -> int:
        """Persist a screenshot, return its assigned id."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError
    
@dataclass(frozen=True, slots=True)
class FeatureLogDTO:
    id: int
    ts: datetime
    app_name: str
    window_title: str
    features: dict  # the 8 SuggestionFeatures fields, flat
    predicted_probability: float
    model_flagged: bool
    user_label: int | None


class FeatureLogRepository(ABC):
    @abstractmethod
    def add(
        self, info: WindowInfo, features: dict, probability: float, flagged: bool
    ) -> int:
        """Persist one feature-vector log entry, return its id."""
        raise NotImplementedError

    @abstractmethod
    def set_label(self, log_id: int, label: int) -> bool:
        """Attach a user feedback label (0 or 1) to a logged entry.
        Returns False if log_id doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def recent_unlabeled(self, limit: int = 10) -> list[FeatureLogDTO]:
        """Most recent entries still awaiting a feedback label —
        what 'cognos feedback' shows the user to label."""
        raise NotImplementedError

    @abstractmethod
    def labeled_examples(self) -> list[FeatureLogDTO]:
        """All entries that have a user_label — this is the real
        training set Day 8's retraining reads from."""
        raise NotImplementedError