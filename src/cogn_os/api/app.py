from __future__ import annotations

from dataclasses import asdict
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from cogn_os.api.schemas import (
    AskRequest,
    AskResponse,
    AssistantCardOut,
    ContextTimelineOut,
    ContextEventIn,
    ExecuteActionRequest,
    ExecuteActionResponse,
    SuggestionOut,
    UserSettingsOut,
    UserSettingsPatch,
)
from cogn_os.actions import ActionExecutor
from cogn_os.assistant.desktop_monitor import DesktopMonitor
from cogn_os.assistant.runtime import AssistantRuntime
from cogn_os.config import Settings, get_settings
from cogn_os.eventing.bus import EventBus, BusEvent
from cogn_os.permissions import permission_inventory
from cogn_os.plugins.events import ContextEvent
from cogn_os.reasoning.types import ReasoningRequest
from cogn_os.safety.rules import RuleEngine
from cogn_os.settings_store import SettingsStore
from cogn_os.storage.factory import get_repositories


def create_app(settings: Settings | None = None, bus: EventBus | None = None) -> FastAPI:
    settings = settings or get_settings()
    bus = bus or EventBus()
    repos = get_repositories(settings)
    rules = RuleEngine()
    actions = ActionExecutor()
    settings_store = SettingsStore()
    runtime = AssistantRuntime(repos.assistant_cards, repos.timeline, bus)
    monitor = DesktopMonitor(settings, runtime, repos.events, bus, settings_store)

    app = FastAPI(title="CognOS Local API", version="0.1.0")
    app.state.bus = bus
    app.state.monitor = monitor
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "app://cognos"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "llm_model": settings.llm_model}

    @app.get("/health/deep")
    def deep_health() -> dict:
        checks = {"api": True}
        try:
            checks["database"] = repos.events.count() >= 0
        except Exception as exc:
            checks["database"] = False
            checks["database_error"] = f"{type(exc).__name__}: {exc}"
        try:
            loaded = settings_store.load()
            checks["settings"] = bool(loaded.llm_model)
        except Exception as exc:
            checks["settings"] = False
            checks["settings_error"] = f"{type(exc).__name__}: {exc}"
        try:
            import ollama

            ollama.Client(host="http://127.0.0.1:11434", timeout=3.0).list()
            checks["ollama"] = True
        except Exception as exc:
            checks["ollama"] = False
            checks["ollama_error"] = f"{type(exc).__name__}: {exc}"
        checks["monitor_running"] = monitor.status.running
        checks["events_seen"] = monitor.status.events_seen
        checks["cards_emitted"] = monitor.status.cards_emitted
        status = "ok" if checks.get("database") and checks.get("settings") else "degraded"
        return {"status": status, "checks": checks}

    @app.on_event("startup")
    async def start_monitor() -> None:
        monitor.start()

    @app.on_event("shutdown")
    async def stop_monitor() -> None:
        await monitor.stop()

    @app.get("/monitor/status")
    def monitor_status() -> dict:
        return asdict(monitor.status)

    @app.get("/permissions")
    def permissions() -> list[dict]:
        return [asdict(p) for p in permission_inventory()]

    @app.get("/settings", response_model=UserSettingsOut)
    def get_user_settings():
        return settings_store.load()

    @app.patch("/settings", response_model=UserSettingsOut)
    async def update_user_settings(payload: UserSettingsPatch):
        updated = settings_store.update(payload.model_dump(exclude_none=True))
        await monitor.restart()
        return updated

    @app.post("/monitor/restart")
    async def restart_monitor() -> dict:
        await monitor.restart()
        return {"ok": True, "status": asdict(monitor.status)}

    @app.get("/model/status")
    def model_status() -> dict:
        try:
            import ollama

            models = ollama.Client(host="http://127.0.0.1:11434", timeout=5.0).list()
            names = [m.get("name") or m.get("model") for m in models.get("models", [])]
            return {
                "reachable": True,
                "configured_model": settings_store.load().llm_model or settings.llm_model,
                "installed_models": names,
            }
        except Exception as exc:
            return {
                "reachable": False,
                "configured_model": settings_store.load().llm_model or settings.llm_model,
                "installed_models": [],
                "error": f"{type(exc).__name__}: {exc}",
            }

    @app.get("/suggestions", response_model=list[SuggestionOut])
    def suggestions(limit: int = 20):
        return repos.suggestions.recent(limit=limit)

    @app.get("/cards", response_model=list[AssistantCardOut])
    def cards(limit: int = 50, include_dismissed: bool = False):
        return repos.assistant_cards.recent(limit=limit, include_dismissed=include_dismissed)

    @app.get("/timeline", response_model=list[ContextTimelineOut])
    def timeline(limit: int = 100):
        return repos.timeline.recent(limit=limit)

    @app.post("/cards/{card_id}/dismiss")
    def dismiss_card(card_id: int) -> dict:
        return {"ok": repos.assistant_cards.set_status(card_id, "dismissed")}

    @app.post("/events/ingest", response_model=list[AssistantCardOut])
    def ingest_event(payload: ContextEventIn):
        event = ContextEvent.now(
            source=payload.source,
            event_type=payload.event_type,
            payload=payload.payload,
            confidence=payload.confidence,
        )
        bus.publish("context_event", {
            "source": event.source,
            "event_type": event.event_type,
            "payload": event.payload,
            "confidence": event.confidence,
            "captured_at": event.captured_at.isoformat(),
        })
        return runtime.ingest([event])

    @app.post("/ask", response_model=AskResponse)
    def ask(payload: AskRequest) -> AskResponse:
        history = repos.events.recent(limit=8)
        context = "\n".join(f"{x.app_name}: {x.window_title}" for x in history)
        findings = rules.evaluate_text(payload.question + "\n" + context)
        try:
            import ollama

            client = ollama.Client(host="http://127.0.0.1:11434", timeout=120.0)
            model = settings_store.load().llm_model or settings.llm_model
            response = client.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are CognOS, a concise local desktop AI assistant. "
                            "Answer the user's direct question clearly. If recent desktop "
                            "context is relevant, use it; otherwise answer from general knowledge. "
                            "Do not return NONE for direct questions."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Recent desktop context:\n{context or '(no captured context yet)'}\n\n"
                            f"Question:\n{payload.question}"
                        ),
                    },
                ],
            )
            answer = response["message"]["content"].strip()
            if not answer:
                answer = "The local model returned an empty answer. Try a shorter question or restart Ollama."
        except Exception as exc:
            answer = (
                "The local LLM is not reachable from CognOS. "
                f"Ollama error: {type(exc).__name__}: {exc}"
            )
        return AskResponse(answer=answer, sources=[asdict(f) for f in findings])

    @app.post("/actions/execute", response_model=ExecuteActionResponse)
    def execute_action(payload: ExecuteActionRequest):
        result = actions.execute(payload.kind, payload.payload, payload.confirmed)
        return ExecuteActionResponse(
            ok=result.ok,
            message=result.message,
            requires_confirmation=result.requires_confirmation,
            result=result.result or {},
        )

    @app.get("/events")
    async def events():
        async def stream():
            async for event in bus.subscribe():
                yield _sse(event)
        return StreamingResponse(stream(), media_type="text/event-stream")

    return app


def _sse(event: BusEvent) -> str:
    data = {"id": event.id, "type": event.type, "payload": event.payload, "created_at": event.created_at.isoformat()}
    return f"event: {event.type}\ndata: {json.dumps(data)}\n\n"
