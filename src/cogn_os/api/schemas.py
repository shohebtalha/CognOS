from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class SuggestionOut(BaseModel):
    id: int
    ts: datetime
    app_name: str
    window_title: str
    suggestion: str


class AssistantActionOut(BaseModel):
    id: str
    label: str
    kind: str
    payload: dict


class AssistantCardOut(BaseModel):
    id: int
    ts: datetime
    kind: str
    severity: str
    title: str
    summary: str
    source: str
    confidence: float
    actions: list[AssistantActionOut]
    context: dict
    status: str


class ContextTimelineOut(BaseModel):
    id: int
    ts: datetime
    source: str
    event_type: str
    summary: str
    payload: dict
    confidence: float | None = None


class ContextEventIn(BaseModel):
    source: str
    event_type: str
    payload: dict = {}
    confidence: float | None = None


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    sources: list[dict] = []


class ExecuteActionRequest(BaseModel):
    kind: str
    payload: dict = {}
    confirmed: bool = False


class ExecuteActionResponse(BaseModel):
    ok: bool
    message: str
    requires_confirmation: bool = False
    result: dict = {}


class UserSettingsOut(BaseModel):
    desktop_monitor_enabled: bool
    ocr_monitor_enabled: bool
    clipboard_monitor_enabled: bool
    native_notifications_enabled: bool
    native_notification_min_severity: str
    llm_model: str
    terminal_monitor_enabled: bool
    terminal_transcript_path: str | None = None
    watched_paths: list[str] | None = None


class UserSettingsPatch(BaseModel):
    desktop_monitor_enabled: bool | None = None
    ocr_monitor_enabled: bool | None = None
    clipboard_monitor_enabled: bool | None = None
    native_notifications_enabled: bool | None = None
    native_notification_min_severity: str | None = None
    llm_model: str | None = None
    terminal_monitor_enabled: bool | None = None
    terminal_transcript_path: str | None = None
    watched_paths: list[str] | None = None
