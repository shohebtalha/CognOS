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

import json

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

    reasoning_provider = None
    try:
        from cogn_os.reasoning.ollama_provider import OllamaReasoningProvider
        reasoning_provider = OllamaReasoningProvider()
        # Quick liveness check so failures surface now, not on first flag.
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

@app.command()
def version() -> None:
    """Print the installed CognOS version."""
    from cogn_os import __version__
    typer.echo(f"CognOS v{__version__}")


if __name__ == "__main__":
    app()

@app.command()
def feedback(count: int = 10) -> None:
    """Review recent unlabeled model decisions and label them y/n.
    This is what builds the real (non-synthetic) training set used by
    'cognos train' — Day 6's model trained purely on synthetic data;
    this is how it gets grounded in your actual judgment."""
    settings = get_settings()
    repos = get_repositories(settings)

    unlabeled = repos.feature_logs.recent_unlabeled(limit=count)
    if not unlabeled:
        typer.echo("No unlabeled entries. Run 'cognos capture' for a while first.")
        return

    typer.echo(f"Labeling {len(unlabeled)} entries. y = worth flagging, n = not, s = skip, q = quit.\n")
    for entry in unlabeled:
        typer.echo(f"[{entry.ts}] {entry.app_name} — {entry.window_title}")
        typer.echo(f"    model predicted: {entry.predicted_probability:.2f} "
                    f"({'FLAGGED' if entry.model_flagged else 'skipped'})")
        answer = typer.prompt("    was this worth flagging? [y/n/s/q]", default="s")

        if answer.lower() == "q":
            break
        if answer.lower() == "y":
            repos.feature_logs.set_label(entry.id, 1)
        elif answer.lower() == "n":
            repos.feature_logs.set_label(entry.id, 0)
        # 's' or anything else: skip, leave unlabeled

    typer.echo("\nDone. Run 'cognos train' once you have enough labeled examples.")


@app.command()
def train() -> None:
    """Retrain the suggestion classifier using real labeled feedback
    (from 'cognos feedback') blended with the synthetic bootstrap
    dataset. Only promotes (overwrites) the production model if the
    new one's test F1 is >= the current production F1 — prints a clear
    before/after comparison either way."""
    import joblib

    from cogn_os.ml.retrain import retrain

    settings = get_settings()
    repos = get_repositories(settings)

    real_examples = repos.feature_logs.labeled_examples()
    typer.echo(f"Found {len(real_examples)} real labeled examples.")

    project_root = Path(__file__).parent.parent.parent
    synthetic_csv = project_root / "data" / "synthetic_events.csv"
    metrics_path = project_root / "models" / "metrics.json"
    model_path = project_root / "models" / "suggestion_classifier.joblib"

    summary, results, pipeline = retrain(synthetic_csv, real_examples, metrics_path)

    typer.echo(f"\nWinner: {summary.winner}")
    typer.echo(f"New F1: {summary.new_f1}")
    typer.echo(f"Previous F1: {summary.previous_f1}")

    if summary.promoted:
        typer.secho(f"PROMOTED — new model is >= previous. Saving.", fg=typer.colors.GREEN)
        joblib.dump(pipeline, model_path)
        metrics_report = {
            "winner": summary.winner,
            "feature_names": list(__import__("cogn_os.ml.features", fromlist=["SuggestionFeatures"]).SuggestionFeatures.FEATURE_NAMES),
            "real_examples_used": summary.real_examples_used,
            "results": results,
        }
        metrics_path.write_text(json.dumps(metrics_report, indent=2))
    else:
        typer.secho(
            f"NOT promoted — new F1 ({summary.new_f1}) is below previous "
            f"({summary.previous_f1}). Production model unchanged.",
            fg=typer.colors.RED,
        )