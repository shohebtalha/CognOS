from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class BusEvent:
    id: str
    type: str
    payload: dict[str, Any]
    created_at: datetime


class EventBus:
    """Tiny in-process pub/sub bus used by the API, desktop UI, and workers."""

    def __init__(self, replay_limit: int = 200) -> None:
        self._subscribers: set[asyncio.Queue[BusEvent]] = set()
        self._recent: deque[BusEvent] = deque(maxlen=replay_limit)

    def publish(self, event_type: str, payload: dict[str, Any]) -> BusEvent:
        event = BusEvent(
            id=str(uuid4()),
            type=event_type,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
        self._recent.append(event)
        for queue in list(self._subscribers):
            queue.put_nowait(event)
        return event

    async def subscribe(self, replay: bool = True):
        queue: asyncio.Queue[BusEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        if replay:
            for event in self._recent:
                queue.put_nowait(event)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)
