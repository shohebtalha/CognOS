"""
Minimal CLI so the capture loop can actually be run as a program. Now
uses the ML-gated loop (Day 7) instead of Day 3's storage-only version
— every window change is logged, and flagged events print to console
(the real LLM-call/notification wiring lands Day 12+; for now,
'flagged' just means 'the trained model thinks this was worth attention').
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from cogn_os.capture.windows_source import WindowsWindowInfoSource
from cogn_os.config import get_settings
from cogn_os.ml.model_suggestion_gate import ModelSuggestionGate
from cogn_os.service.clock import RealClock
from cogn_os.service.wiring import build_ml_gated_loop
from cogn_os.storage.factory import get_repositories

app = typer.Typer()

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "suggestion_classifier.joblib"


@app.command()
def capture() -> None:
    """Run the ML-gated capture loop in the foreground. Ctrl+C to stop."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    repos = get_repositories(settings)
    source = WindowsWindowInfoSource()
    gate = ModelSuggestionGate(model_path=MODEL_PATH)

    def on_flagged(info) -> None:
        typer.secho(f"[FLAGGED] {info.app_name} — {info.window_title}", fg=typer.colors.YELLOW)

    loop = build_ml_gated_loop(settings, source, RealClock(), repos.events, gate, on_flagged)

    typer.echo(f"CognOS capture running (ML-gated). Logging to {settings.database_url}")
    try:
        loop.run()
    except KeyboardInterrupt:
        loop.stop()
        typer.echo("\nStopped.")


@app.command()
def version() -> None:
    """Print the installed CognOS version."""
    from cogn_os import __version__
    typer.echo(f"CognOS v{__version__}")


if __name__ == "__main__":
    app()