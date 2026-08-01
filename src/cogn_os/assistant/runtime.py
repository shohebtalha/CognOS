from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from typing import Iterable

from cogn_os.assistant.policies import OpportunityDetector
from cogn_os.assistant.types import AssistantAction, AssistantCard, CardSeverity, WorkspaceState
from cogn_os.eventing.bus import EventBus
from cogn_os.plugins.events import ContextEvent
from cogn_os.privacy import redact_payload
from cogn_os.storage.repository import (
    AssistantActionDTO,
    AssistantCardDTO,
    AssistantCardRepository,
    ContextTimelineRepository,
)


class AssistantRuntime:
    """Product runtime: keeps workspace state and emits assistant cards."""

    def __init__(
        self,
        cards: AssistantCardRepository,
        timeline: ContextTimelineRepository | None = None,
        bus: EventBus | None = None,
        detector: OpportunityDetector | None = None,
    ) -> None:
        self._cards = cards
        self._timeline = timeline
        self._bus = bus or EventBus()
        self._detector = detector or OpportunityDetector()
        self._active_app: str | None = None
        self._active_title: str | None = None
        self._visible_text: str | None = None
        self._recent: list[str] = []
        self._recent_card_hashes: dict[str, datetime] = {}
        self._dedupe_seconds = 180.0

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
            redacted_event = ContextEvent(
                source=event.source,
                event_type=event.event_type,
                payload=redact_payload(event.payload),
                confidence=event.confidence,
                captured_at=event.captured_at,
            )
            self._update_state(redacted_event)
            if self._timeline is not None:
                self._timeline.add_event(
                    source=redacted_event.source,
                    event_type=redacted_event.event_type,
                    summary=_summarize_event(redacted_event),
                    payload=redacted_event.payload,
                    ts=redacted_event.captured_at,
                    confidence=redacted_event.confidence,
                )
            for card in self._detector.evaluate(event, self.state):
                if self._is_duplicate_card(card):
                    continue
                dto = self._cards.add(_to_dto(_redact_card(card)))
                self._bus.publish("assistant_card", _card_payload(dto))
                emitted.append(dto)
        return emitted

    def _is_duplicate_card(self, card: AssistantCard) -> bool:
        key = hashlib.sha256(f"{card.kind}|{card.title}|{card.summary}|{card.source}".encode()).hexdigest()
        now = datetime.now(timezone.utc)
        previous = self._recent_card_hashes.get(key)
        self._recent_card_hashes = {
            k: v for k, v in self._recent_card_hashes.items()
            if (now - v).total_seconds() < self._dedupe_seconds
        }
        if previous is not None and (now - previous).total_seconds() < self._dedupe_seconds:
            return True
        self._recent_card_hashes[key] = now
        return False

    def _update_state(self, event: ContextEvent) -> None:
        self._recent.append(f"{event.source}:{event.event_type}")
        if len(self._recent) > 100:
            self._recent = self._recent[-100:]
        if event.event_type == "window_changed":
            self._active_app = str(event.payload.get("app_name") or event.payload.get("app") or "")
            self._active_title = str(event.payload.get("window_title") or event.payload.get("title") or "")
        elif event.event_type == "screen_text_detected":
            self._visible_text = str(event.payload.get("text", ""))

    def synthesize(self) -> list[AssistantCardDTO]:
        if self._timeline is None:
            return []
        recent = self._timeline.recent(limit=25)
        if not recent:
            return []
        summaries = [item.summary for item in recent[:10]]
        cards: list[AssistantCardDTO] = []
        if sum("window_tracker:window_changed" in s for s in summaries) >= 6:
            card = AssistantCard(
                kind="productivity",
                severity=CardSeverity.INFO,
                title="Rapid context switching",
                summary="CognOS noticed several window changes recently. It may help to consolidate the current task or ask for a summary.",
                source="proactive_synthesizer",
                confidence=0.72,
                actions=(AssistantAction("summarize_context", "Summarize", "ask", {"prompt": "Summarize my recent desktop activity and suggest one next step."}),),
                context={"recent": summaries},
            )
            if not self._is_duplicate_card(card):
                cards.append(self._cards.add(_to_dto(card)))
        for card in cards:
            self._bus.publish("assistant_card", _card_payload(card))
        return cards


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


def _redact_card(card: AssistantCard) -> AssistantCard:
    return AssistantCard(
        kind=card.kind,
        severity=card.severity,
        title=card.title,
        summary=card.summary,
        source=card.source,
        confidence=card.confidence,
        actions=tuple(
            AssistantAction(a.id, a.label, a.kind, redact_payload(a.payload))
            for a in card.actions
        ),
        context=redact_payload(card.context),
        created_at=card.created_at,
    )


def _card_payload(card: AssistantCardDTO) -> dict:
    payload = asdict(card)
    payload["ts"] = card.ts.isoformat()
    return payload


def _summarize_event(event: ContextEvent) -> str:
    if event.event_type == "window_changed":
        return f"{event.source}:{event.event_type} {event.payload.get('app_name', '')} {event.payload.get('window_title', '')}".strip()
    if event.event_type == "browser_navigation":
        return f"{event.source}:{event.event_type} {event.payload.get('title', '')} {event.payload.get('url', '')}".strip()
    if event.event_type == "editor_diagnostic":
        return f"{event.source}:{event.event_type} {event.payload.get('file_name', '')}".strip()
    if event.event_type == "terminal_output":
        return f"{event.source}:{event.event_type} {str(event.payload.get('text', ''))[:300]}".strip()
    if "text" in event.payload:
        return f"{event.source}:{event.event_type} {str(event.payload.get('text'))[:300]}".strip()
    return f"{event.source}:{event.event_type}"
