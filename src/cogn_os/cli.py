"""
CognOS CLI. `capture` now runs on PluginOrchestrator (plugin
architecture) instead of the old build_ml_gated_loop/CaptureLoop path
— this is the real cutover point. WindowObserver is registered as the
only plugin today; OCR/clipboard/etc. plugins register here too once
built, with zero changes to the orchestrator itself.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from cogn_os.capture.windows_source import WindowsWindowInfoSource
from cogn_os.config import get_settings
from cogn_os.ml.model_suggestion_gate import ModelSuggestionGate
from cogn_os.plugins.orchestrator import PluginOrchestrator
from cogn_os.plugins.registry import PluginRegistry
from cogn_os.plugins.window_observer import WindowObserver
from cogn_os.service.clock import RealClock
from cogn_os.storage.factory import get_repositories

app = typer.Typer()

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "suggestion_classifier.joblib"


@app.command()
def capture() -> None:
    """Run the plugin-based capture/reasoning loop in the foreground.
    Ctrl+C to stop."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    repos = get_repositories(settings)
    gate = ModelSuggestionGate(model_path=MODEL_PATH)

    reasoning_provider = None
    try:
        from cogn_os.reasoning.ollama_provider import OllamaReasoningProvider
        reasoning_provider = OllamaReasoningProvider()
        import ollama
        ollama.Client().list()
    except Exception:
        typer.secho(
            "WARNING: Ollama not reachable (is 'ollama serve' running with "
            "a model pulled?) — flagged events will be logged but no "
            "suggestion will be generated.",
            fg=typer.colors.YELLOW,
        )
        reasoning_provider = None

    def on_flagged(info, history) -> None:
        from cogn_os.context.privacy_filter import is_sensitive

        if is_sensitive(info):
            typer.secho(f"[FLAGGED but SKIPPED - sensitive content] {info.app_name}", fg=typer.colors.RED)
            return

        typer.secho(f"[FLAGGED] {info.app_name} — {info.window_title}", fg=typer.colors.YELLOW)
        if reasoning_provider is None:
            return

        from cogn_os.context.builder import build_context_summary
        from cogn_os.reasoning.types import ReasoningRequest

        context_summary = build_context_summary(history=history, current=info)
        request = ReasoningRequest(
            context_summary=context_summary,
            current_app=info.app_name,
            current_window_title=info.window_title,
        )
        result = reasoning_provider.get_suggestion(request)
        if result.suggestion:
            typer.secho(f"  -> SUGGESTION: {result.suggestion}", fg=typer.colors.GREEN)
            repos.suggestions.add(info, result.suggestion)
        else:
            typer.echo("  -> (model had nothing useful to say)")

    clock = RealClock()
    registry = PluginRegistry(clock)
    registry.register(WindowObserver(WindowsWindowInfoSource(), poll_interval=settings.poll_interval_seconds))
    # Future plugins register here — OCR, clipboard, etc. — with zero
    # changes to PluginOrchestrator itself.

    orchestrator = PluginOrchestrator(
        registry, clock, settings, repos.events, gate, on_flagged,
        feature_log_repo=repos.feature_logs,
        tick_interval_seconds=1.0,
    )

    typer.echo(f"CognOS capture running (plugin architecture, local LLM). Logging to {settings.database_url}")
    typer.echo(f"Registered plugins: {registry.registered_names}")
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        orchestrator.stop()
        typer.echo("\nStopped.")


@app.command()
def version() -> None:
    """Print the installed CognOS version."""
    from cogn_os import __version__
    typer.echo(f"CognOS v{__version__}")


if __name__ == "__main__":
    app()