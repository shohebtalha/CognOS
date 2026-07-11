"""
Shared pytest fixtures. `sqlite_session_factory` spins up a fresh
in-memory SQLite DB per test — tables created from the same
Base.metadata used in production, so schema drift between test and real
DB is impossible by construction (no separate "test schema" to go stale).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from cogn_os.storage.models import Base


@pytest.fixture
def sqlite_session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)