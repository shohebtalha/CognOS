from __future__ import annotations

from dataclasses import dataclass

from cogn_os.config import Settings
from cogn_os.storage.database import make_engine, make_session_factory
from cogn_os.storage.models import Base
from cogn_os.storage.repository import (
    EventRepository, FeatureLogRepository, ScreenshotRepository, SuggestionRepository,
)
from cogn_os.storage.sqlalchemy_repository import (
    SqlAlchemyEventRepository, SqlAlchemyFeatureLogRepository,
    SqlAlchemyScreenshotRepository, SqlAlchemySuggestionRepository,
)


@dataclass(frozen=True)
class Repositories:
    events: EventRepository
    suggestions: SuggestionRepository
    screenshots: ScreenshotRepository
    feature_logs: FeatureLogRepository


def get_repositories(settings: Settings, create_tables: bool = True) -> Repositories:
    engine = make_engine(settings)
    if create_tables:
        Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    return Repositories(
        events=SqlAlchemyEventRepository(session_factory),
        suggestions=SqlAlchemySuggestionRepository(session_factory),
        screenshots=SqlAlchemyScreenshotRepository(session_factory),
        feature_logs=SqlAlchemyFeatureLogRepository(session_factory),
    )