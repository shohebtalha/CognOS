"""
Compares two "is this a real context change" strategies against the
hand-labeled evaluation set:
  1. Naive baseline: exact string inequality (what CaptureLoop used
     through Day 9 — any title diff at all counts as "different")
  2. Semantic: SemanticChangeDetector's cosine-similarity threshold

Reports accuracy for both, plus a sweep across candidate thresholds so
the chosen DEFAULT_SIMILARITY_THRESHOLD in change_detector.py is a
measured choice, not a guess.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cogn_os.embeddings.change_detector import SemanticChangeDetector  # noqa: E402
from cogn_os.embeddings.sentence_transformer_provider import SentenceTransformerProvider  # noqa: E402

EVAL_PATH = Path(__file__).parent.parent / "data" / "title_pairs_eval.csv"


def load_pairs() -> list[dict]:
    with EVAL_PATH.open() as f:
        return list(csv.DictReader(f))


def naive_baseline_accuracy(pairs: list[dict]) -> float:
    correct = 0
    for row in pairs:
        # naive rule: "different" whenever strings aren't identical
        predicted_same = row["title_a"] == row["title_b"]
        actual_same = row["same_context"] == "1"
        if predicted_same == actual_same:
            correct += 1
    return correct / len(pairs)


def semantic_accuracy(pairs: list[dict], detector: SemanticChangeDetector) -> float:
    correct = 0
    for row in pairs:
        decision = detector.compare(row["title_a"], row["title_b"])
        predicted_same = not decision.is_different
        actual_same = row["same_context"] == "1"
        if predicted_same == actual_same:
            correct += 1
    return correct / len(pairs)


def threshold_sweep(pairs: list[dict], provider) -> None:
    print("\nThreshold sweep:")
    best_threshold, best_accuracy = None, -1.0
    for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
        detector = SemanticChangeDetector(provider, threshold=threshold)
        acc = semantic_accuracy(pairs, detector)
        marker = ""
        if acc > best_accuracy:
            best_accuracy = acc
            best_threshold = threshold
            marker = "  <- best so far"
        print(f"  threshold={threshold:.2f}  accuracy={acc:.2%}{marker}")
    print(f"\nBest threshold: {best_threshold} (accuracy={best_accuracy:.2%})")


def main() -> None:
    pairs = load_pairs()
    provider = SentenceTransformerProvider()

    naive_acc = naive_baseline_accuracy(pairs)
    default_detector = SemanticChangeDetector(provider)  # uses DEFAULT_SIMILARITY_THRESHOLD
    semantic_acc = semantic_accuracy(pairs, default_detector)

    print(f"Naive string-match baseline accuracy:  {naive_acc:.2%}")
    print(f"Semantic (default threshold) accuracy: {semantic_acc:.2%}")
    print(f"Improvement: {(semantic_acc - naive_acc) * 100:+.1f} percentage points")

    threshold_sweep(pairs, provider)


if __name__ == "__main__":
    main()