from __future__ import annotations

from dataclasses import dataclass, fields
from typing import ClassVar

from cogn_os.ml.app_category import AppCategory


@dataclass(frozen=True, slots=True)
class SuggestionFeatures:
    # --- timing ---
    seconds_since_last_llm_call: float
    hour_of_day: int          # 0-23
    is_weekend: bool

    # --- app context ---
    app_category: AppCategory
    title_length: int
    app_changed: bool          # False if only the title changed within the same app
    is_first_time_app_today: bool

    # --- recent activity pattern ---
    switches_last_5min: int    # rolling count of window changes in the last 5 minutes

    FEATURE_NAMES: ClassVar[tuple[str, ...]] = (
        "seconds_since_last_llm_call",
        "hour_of_day",
        "is_weekend",
        "app_category",
        "title_length",
        "app_changed",
        "is_first_time_app_today",
        "switches_last_5min",
    )

    def to_dict(self) -> dict[str, object]:
        return {f.name: getattr(self, f.name) for f in fields(self)}