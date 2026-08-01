"""
SQLAlchemy engine/session factory. Kept as a factory (not a module-level
global engine) so tests can point at an in-memory SQLite DB
("sqlite:///:memory:") without touching the real cognos.db file, and so
the connection string is always sourced from Settings rather than
hardcoded.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

from cogn_os.config import Settings


def make_engine(settings: Settings) -> Engine:
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # SQLite + threads: allow the connection to be used outside the
        # thread that created it. Safe here because our access pattern is
        # one session per unit of work, not shared long-lived connections.
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def ensure_sqlite_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required = {
        "assistant_cards": {
            "id": "INTEGER",
            "ts": "DATETIME",
            "kind": "VARCHAR(64)",
            "severity": "VARCHAR(24)",
            "title": "VARCHAR(255)",
            "summary": "TEXT",
            "source": "VARCHAR(128)",
            "confidence": "FLOAT",
            "actions_json": "TEXT DEFAULT '[]'",
            "context_json": "TEXT DEFAULT '{}'",
            "status": "VARCHAR(24) DEFAULT 'new'",
        },
        "context_timeline": {
            "id": "INTEGER",
            "ts": "DATETIME",
            "source": "VARCHAR(128)",
            "event_type": "VARCHAR(128)",
            "summary": "TEXT",
            "payload_json": "TEXT DEFAULT '{}'",
            "confidence": "FLOAT",
        },
    }
    with engine.begin() as conn:
        for table, columns in required.items():
            if table not in existing_tables:
                continue
            current = {col["name"] for col in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name in current or name == "id":
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield a session, commit on success, rollback on error, always close.
    This is the only place commit/rollback logic lives — callers never
    manage transactions manually."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
