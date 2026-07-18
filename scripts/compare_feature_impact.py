"""
Compares the Day 6 baseline (8 features, no semantic similarity) against
the Day 11 retrain (9 features, with semantic similarity) on the SAME
held-out evaluation methodology — this is the actual answer to "did
the new feature help," stated in numbers rather than assumed.

Important honesty note: this comparison is NOT perfectly apples-to-apples
— the underlying synthetic dataset also changed (Commit #1's updated
label heuristic), so any delta reflects both the new feature AND the
updated labeling logic together, not the feature in isolation. This
script states that caveat explicitly rather than overselling the result.
"""

from __future__ import annotations

import json
from pathlib import Path

BASELINE_PATH = Path(__file__).parent.parent / "models" / "metrics_day6_baseline.json"
CURRENT_PATH = Path(__file__).parent.parent / "models" / "metrics.json"


def main() -> None:
    baseline = json.loads(BASELINE_PATH.read_text())
    current = json.loads(CURRENT_PATH.read_text())

    baseline_winner = baseline["winner"]
    current_winner = current["winner"]

    baseline_f1 = baseline["results"][baseline_winner]["test_set"]["f1"]
    current_f1 = current["results"][current_winner]["test_set"]["f1"]

    baseline_precision = baseline["results"][baseline_winner]["test_set"]["precision"]
    current_precision = current["results"][current_winner]["test_set"]["precision"]

    baseline_recall = baseline["results"][baseline_winner]["test_set"]["recall"]
    current_recall = current["results"][current_winner]["test_set"]["recall"]

    print("=" * 60)
    print("BEFORE (Day 6, 8 features)  vs  AFTER (Day 11, 9 features)")
    print("=" * 60)
    print(f"Winner model:  {baseline_winner:20s} -> {current_winner}")
    print(f"Test F1:       {baseline_f1:.4f}{' ' * 14} -> {current_f1:.4f}  ({current_f1 - baseline_f1:+.4f})")
    print(f"Precision:     {baseline_precision:.4f}{' ' * 14} -> {current_precision:.4f}  ({current_precision - baseline_precision:+.4f})")
    print(f"Recall:        {baseline_recall:.4f}{' ' * 14} -> {current_recall:.4f}  ({current_recall - baseline_recall:+.4f})")
    print()
    print("CAVEAT: the synthetic dataset's label heuristic also changed")
    print("alongside the new feature (see generate_training_data.py),")
    print("so this delta reflects both changes together, not the new")
    print("feature in perfect isolation. Documented honestly, not hidden.")


if __name__ == "__main__":
    main()