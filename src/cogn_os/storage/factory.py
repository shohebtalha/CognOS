"""
One place that assembles the storage layer from Settings — engine,
session factory, table creation, and all repositories. The rest of the
app (capture loop, API, CLI) calls get_repositories() once at startup
instead of each constructing engines/sessions itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from cogn_os.config import Settings
from cogn_os.storage.database import make_engine, make_session_factory
from cogn_os.storage.models import Base
from cogn_os.storage.repository import EventRepository, ScreenshotRepository, SuggestionRepository
from cogn_os.storage.sqlalchemy_repository import (
    SqlAlchemyEventRepository,
    SqlAlchemyScreenshotRepository,
    SqlAlchemySuggestionRepository,
)


@dataclass(frozen=True)
class Repositories:
    events: EventRepository
    suggestions: SuggestionRepository
    screenshots: ScreenshotRepository


def get_repositories(settings: Settings, create_tables: bool = True) -> Repositories:
    engine = make_engine(settings)
    if create_tables:
        Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    return Repositories(
        events=SqlAlchemyEventRepository(session_factory),
        suggestions=SqlAlchemySuggestionRepository(session_factory),
        screenshots=SqlAlchemyScreenshotRepository(session_factory),
    )