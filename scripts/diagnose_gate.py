"""
Standalone diagnostic: watches real window changes and prints the
model's raw predicted probability (not just the thresholded True/False)
alongside the feature values that produced it. Does NOT write to the
real database or affect the live capture loop — safe to run alongside
or instead of `cognos capture` for debugging/demonstration purposes.

Run: python scripts/diagnose_gate.py
Ctrl+C to stop.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cogn_os.capture.windows_source import WindowsWindowInfoSource  # noqa: E402
from cogn_os.ml.context_tracker import ContextTracker  # noqa: E402
from cogn_os.ml.feature_extractor import FeatureExtractor  # noqa: E402
from cogn_os.ml.model_suggestion_gate import ModelSuggestionGate  # noqa: E402

MODEL_PATH = Path(__file__).parent.parent / "models" / "suggestion_classifier.joblib"


def main() -> None:
    source = WindowsWindowInfoSource()
    tracker = ContextTracker()
    extractor = FeatureExtractor()
    gate = ModelSuggestionGate(model_path=MODEL_PATH)

    last_seen = None
    print("Watching window changes. Ctrl+C to stop.\n")

    try:
        while True:
            info = source.get_active_window()
            if info is None:
                time.sleep(2)
                continue

            changed = last_seen is None or (
                info.app_name != last_seen.app_name or info.window_title != last_seen.window_title
            )
            if changed:
                features = extractor.extract(
                    current=info,
                    previous=tracker.previous,
                    history=tracker.history,
                    last_llm_call_at=tracker.last_llm_call_at,
                    apps_seen_today=tracker.apps_seen_today,
                )
                probability = gate.predict_probability(features)
                decision = "FLAG" if probability >= 0.5 else "skip"

                print(f"{info.app_name:30s} prob={probability:.3f}  [{decision}]")
                print(f"    first_time_today={features.is_first_time_app_today}  "
                      f"app_changed={features.app_changed}  "
                      f"switches_5min={features.switches_last_5min}  "
                      f"category={features.app_category.value}  "
                      f"sec_since_call={features.seconds_since_last_llm_call:.0f}")

                tracker.record_event(info)
                tracker.set_previous(info)
                if probability >= 0.5:
                    tracker.record_llm_call(info.captured_at)

                last_seen = info

            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()