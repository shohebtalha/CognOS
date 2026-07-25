from datetime import datetime, timezone

from cogn_os.assistant.runtime import AssistantRuntime
from cogn_os.plugins.events import ContextEvent
from cogn_os.storage.repository import AssistantCardDTO, AssistantCardRepository


class InMemoryCardRepo(AssistantCardRepository):
    def __init__(self) -> None:
        self.cards: list[AssistantCardDTO] = []

    def add(self, card: AssistantCardDTO) -> AssistantCardDTO:
        saved = AssistantCardDTO(
            id=len(self.cards) + 1,
            ts=card.ts,
            kind=card.kind,
            severity=card.severity,
            title=card.title,
            summary=card.summary,
            source=card.source,
            confidence=card.confidence,
            actions=card.actions,
            context=card.context,
            status=card.status,
        )
        self.cards.append(saved)
        return saved

    def recent(self, limit: int = 50, include_dismissed: bool = False) -> list[AssistantCardDTO]:
        return self.cards[-limit:]

    def set_status(self, card_id: int, status: str) -> bool:
        return True


def test_runtime_emits_debug_card_for_traceback():
    repo = InMemoryCardRepo()
    runtime = AssistantRuntime(repo)

    cards = runtime.ingest([
        ContextEvent(
            source="ocr",
            event_type="screen_text_detected",
            payload={"text": "Traceback (most recent call last):\nSyntaxError: invalid syntax"},
            confidence=0.96,
            captured_at=datetime.now(timezone.utc),
        )
    ])

    assert len(cards) == 1
    assert cards[0].kind == "debugging"
    assert cards[0].severity == "critical"
    assert cards[0].actions[0].kind == "ask"
