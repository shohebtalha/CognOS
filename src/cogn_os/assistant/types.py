from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CardSeverity(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AssistantAction:
    id: str
    label: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AssistantCard:
    kind: str
    severity: CardSeverity
    title: str
    summary: str
    source: str
    confidence: float = 1.0
    actions: tuple[AssistantAction, ...] = ()
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    active_app: str | None
    active_title: str | None
    visible_text: str | None
    recent_events: tuple[str, ...]
    risk_level: CardSeverity
