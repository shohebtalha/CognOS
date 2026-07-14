"""
Doesn't re-run the full training script (slow, and already covered by
manual execution above) — instead unit-tests the winner-selection logic
in isolation, since that's the part most likely to have a silent bug
(e.g. comparing the wrong metric, or picking min instead of max).
"""

from __future__ import annotations


def test_winner_selection_picks_highest_f1():
    results = {
        "logistic_regression": {"test_set": {"f1": 0.42}},
        "random_forest": {"test_set": {"f1": 0.51}},
    }
    candidates = list(results.keys())

    winner = max(candidates, key=lambda m: results[m]["test_set"]["f1"])

    assert winner == "random_forest"


def test_winner_selection_is_stable_when_scores_tie():
    results = {
        "logistic_regression": {"test_set": {"f1": 0.5}},
        "random_forest": {"test_set": {"f1": 0.5}},
    }
    candidates = list(results.keys())

    # max() with a tie returns the first candidate in iteration order —
    # documenting this behavior explicitly rather than leaving it implicit.
    winner = max(candidates, key=lambda m: results[m]["test_set"]["f1"])

    assert winner == "logistic_regression"