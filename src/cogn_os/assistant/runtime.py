from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from cogn_os.assistant.policies import OpportunityDetector
from cogn_os.assistant.types import AssistantCard, CardSeverity, WorkspaceState
from cogn_os.eventing.bus import EventBus
from cogn_os.plugins.events import ContextEvent
from cogn_os.storage.repository import (
    AssistantActionDTO,
    AssistantCardDTO,
    AssistantCardRepository,
)


class AssistantRuntime:
    """Product runtime: keeps workspace state and emits assistant cards."""

    def __init__(
        self,
        cards: AssistantCardRepository,
        bus: EventBus | None = None,
        detector: OpportunityDetector | None = None,
    ) -> None:
        self._cards = cards
        self._bus = bus or EventBus()
        self._detector = detector or OpportunityDetector()
        self._active_app: str | None = None
        self._active_title: str | None = None
        self._visible_text: str | None = None
        self._recent: list[str] = []

    @property
    def state(self) -> WorkspaceState:
        return WorkspaceState(
            active_app=self._active_app,
            active_title=self._active_title,
            visible_text=self._visible_text,
            recent_events=tuple(self._recent[-25:]),
            risk_level=CardSeverity.INFO,
        )

    def ingest(self, events: Iterable[ContextEvent]) -> list[AssistantCardDTO]:
        emitted: list[AssistantCardDTO] = []
        for event in events:
            self._update_state(event)
            for card in self._detector.evaluate(event, self.state):
                dto = self._cards.add(_to_dto(card))
                self._bus.publish("assistant_card", _card_payload(dto))
                emitted.append(dto)
        return emitted

    def _update_state(self, event: ContextEvent) -> None:
        self._recent.append(f"{event.source}:{event.event_type}")
        if len(self._recent) > 100:
            self._recent = self._recent[-100:]
        if event.event_type == "window_changed":
            self._active_app = str(event.payload.get("app_name") or event.payload.get("app") or "")
            self._active_title = str(event.payload.get("window_title") or event.payload.get("title") or "")
        elif event.event_type == "screen_text_detected":
            self._visible_text = str(event.payload.get("text", ""))


def _to_dto(card: AssistantCard) -> AssistantCardDTO:
    return AssistantCardDTO(
        id=0,
        ts=card.created_at,
        kind=card.kind,
        severity=card.severity.value,
        title=card.title,
        summary=card.summary,
        source=card.source,
        confidence=card.confidence,
        actions=[
            AssistantActionDTO(id=a.id, label=a.label, kind=a.kind, payload=a.payload)
            for a in card.actions
        ],
        context=card.context,
        status="new",
    )


def _card_payload(card: AssistantCardDTO) -> dict:
    payload = asdict(card)
    payload["ts"] = card.ts.isoformat()
    return payload
