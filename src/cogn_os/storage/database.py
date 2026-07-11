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