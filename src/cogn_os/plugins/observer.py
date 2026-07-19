"""
Observer is the interface for IN-PROCESS plugins (OCR, clipboard,
system/Explorer, window tracking) — ones that run as part of the
CognOS Python process itself, as opposed to application-integration
plugins (browser extension, VS Code extension) which run inside
another program and talk to CognOS over the ingestion endpoint
(see plugins/ingestion.py) instead of implementing this interface.

Deliberately a poll-based interface (poll() -> list[ContextEvent]),
not a push/callback-based one — this keeps every observer trivially
testable (call poll() in a test, inspect the returned list) without
threading, event loops, or timing concerns bleeding into plugin
implementations. The PluginRegistry (registry.py) is responsible for
calling poll() on a schedule per-observer; individual observers stay
simple and synchronous.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cogn_os.plugins.events import ContextEvent


class Observer(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier, used as ContextEvent.source."""
        raise NotImplementedError

    @property
    def poll_interval_seconds(self) -> float:
        """How often the registry should call poll() on this observer.
        Default 5s; override for cheaper/more expensive observers
        (e.g. clipboard can poll every 1s cheaply; OCR should poll
        much less often since it's comparatively expensive)."""
        return 5.0

    @abstractmethod
    def poll(self) -> list[ContextEvent]:
        """Check for new observations since the last call and return
        them as ContextEvents. Return an empty list if nothing new.
        Must NEVER raise — implementations should catch their own
        errors internally and return [] on failure, since a single
        misbehaving plugin must not be able to crash the registry loop
        that drives all other plugins."""
        raise NotImplementedError