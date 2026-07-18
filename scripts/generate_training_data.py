"""
Generates a synthetic training dataset for the suggestion-worthiness
classifier, used to cold-start the model before real usage logs exist
(see Day 8, which retrains on real data once it's been collected).

LABELING METHODOLOGY (documented explicitly — this is what makes a
synthetic dataset defensible rather than made-up):

A simulated event is labeled `worth_flagging=1` if it matches heuristics
that correlate with genuinely interesting moments in real usage:
  - First time seeing an app today (novel context)         -> weight
  - Rapid app switching (>=3 switches in 5 min => "thrashing",
    often precedes/accompanies frustration or debugging)   -> weight
  - Long gap since last LLM call AND an app change          -> weight
  - IDE or terminal app changes (more often actionable than
    e.g. chat apps)                                         -> weight
Each factor contributes an independent probability bump; final label
is a Bernoulli draw from the combined probability, not a hard rule —
this avoids a linearly-separable synthetic dataset that would make the
classifier trivially perfect and useless as a real evaluation.

This script's output (data/synthetic_events.csv) is what Day 6 trains
on. Once Day 8 lands, `cognos train` retrains on real collected data
and this synthetic set becomes purely a smoke-test/cold-start fixture.
"""

from __future__ import annotations

import csv
import random
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cogn_os.capture.types import WindowInfo
from cogn_os.ml.feature_extractor import FeatureExtractor

from cogn_os.embeddings.change_detector import SemanticChangeDetector
from cogn_os.embeddings.sentence_transformer_provider import SentenceTransformerProvider

APPS = [
    "code.exe", "chrome.exe", "windowsterminal.exe", "slack.exe",
    "whatsapp.root.exe", "winword.exe", "explorer.exe", "outlook.exe",
]

TITLES_BY_APP = {
    "code.exe": ["main.py - CognOS", "test_feature_extractor.py", "Traceback (most recent call last)"],
    "chrome.exe": ["Stack Overflow - Python error", "Gmail", "YouTube"],
    "windowsterminal.exe": ["pytest tests/ -v", "npm install", "git commit"],
    "slack.exe": ["#general", "#engineering", "DM: manager"],
    "whatsapp.root.exe": ["WhatsApp"],
    "winword.exe": ["Report.docx - Word"],
    "explorer.exe": [""],
    "outlook.exe": ["Inbox - Outlook"],
}


def _label_probability(features_dict: dict, app_name: str) -> float:
    p = 0.05  # base rate: most events are not worth flagging
    if features_dict["is_first_time_app_today"]:
        p += 0.25
    if features_dict["switches_last_5min"] >= 3:
        p += 0.30
    if features_dict["seconds_since_last_llm_call"] > 300 and features_dict["app_changed"]:
        p += 0.15
    if app_name in ("code.exe", "windowsterminal.exe"):
        p += 0.10
    similarity = features_dict.get("title_semantic_similarity_to_previous", 0.5)
    if similarity < 0.4:
        p += 0.20
    return min(p, 0.9)

def generate_session(rng: random.Random, start: datetime, num_events: int) -> list[WindowInfo]:
    events = []
    t = start
    for _ in range(num_events):
        app = rng.choice(APPS)
        title = rng.choice(TITLES_BY_APP[app])
        t += timedelta(seconds=rng.randint(5, 240))
        events.append(WindowInfo(app_name=app, window_title=title, captured_at=t))
    return events


def build_dataset(num_sessions: int = 40, events_per_session: int = 60, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    provider = SentenceTransformerProvider()
    change_detector = SemanticChangeDetector(provider)
    extractor = FeatureExtractor(change_detector=change_detector)
    rows: list[dict] = []

    for session_idx in range(num_sessions):
        session_start = datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(days=session_idx, hours=9)
        events = generate_session(rng, session_start, events_per_session)

        apps_seen_today: set[str] = set()
        last_llm_call_at: datetime | None = None
        history: list[WindowInfo] = []

        for i, event in enumerate(events):
            previous = events[i - 1] if i > 0 else None
            features = extractor.extract(
                current=event, previous=previous, history=history,
                last_llm_call_at=last_llm_call_at, apps_seen_today=apps_seen_today,
            )
            fdict = features.to_dict()
            fdict["app_category"] = fdict["app_category"].value  # enum -> str for CSV

            prob = _label_probability(features.to_dict(), event.app_name)
            label = 1 if rng.random() < prob else 0

            row = {**fdict, "worth_flagging": label}
            rows.append(row)

            history.append(event)
            apps_seen_today.add(event.app_name)
            if label == 1:
                last_llm_call_at = event.captured_at

    return rows


def write_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    rows = build_dataset()
    out_path = Path(__file__).parent.parent / "data" / "synthetic_events.csv"
    write_csv(rows, out_path)
    positive_rate = sum(r["worth_flagging"] for r in rows) / len(rows)
    print(f"wrote {len(rows)} rows to {out_path}")
    print(f"positive rate: {positive_rate:.2%}")