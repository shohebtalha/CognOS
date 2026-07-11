"""
Minimal CLI so the capture loop can actually be run as a program, not
just exercised in tests. Full start/stop/status/export commands land
Day 13 — this is deliberately just enough to prove Day 3's checkpoint:
'cognos capture' runs standalone and logs a real timeline to SQLite.
"""

from __future__ import annotations

import logging

import typer

from cogn_os.capture.windows_source import WindowsWindowInfoSource
from cogn_os.config import get_settings
from cogn_os.service.clock import RealClock
from cogn_os.service.wiring import build_storage_backed_loop
from cogn_os.storage.factory import get_repositories

app = typer.Typer()


@app.command()
def capture() -> None:
    """Run the capture loop in the foreground. Ctrl+C to stop."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    repos = get_repositories(settings)
    source = WindowsWindowInfoSource()
    loop = build_storage_backed_loop(settings, source, RealClock(), repos.events)

    typer.echo(f"CognOS capture running. Logging to {settings.database_url}")
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