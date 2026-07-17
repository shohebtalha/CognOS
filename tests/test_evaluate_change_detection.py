import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.evaluate_change_detection import naive_baseline_accuracy, semantic_accuracy  # noqa: E402
from cogn_os.embeddings.change_detector import SemanticChangeDetector  # noqa: E402
from cogn_os.embeddings.fake_provider import FakeEmbeddingProvider  # noqa: E402


def test_naive_baseline_scores_identical_strings_as_same():
    pairs = [{"title_a": "x", "title_b": "x", "same_context": "1"}]
    assert naive_baseline_accuracy(pairs) == 1.0


def test_naive_baseline_scores_any_diff_as_different():
    # naive rule treats ANY string difference as "not same" — this
    # correctly scores a genuinely-different pair as correct...
    pairs = [{"title_a": "x", "title_b": "y", "same_context": "0"}]
    assert naive_baseline_accuracy(pairs) == 1.0


def test_naive_baseline_fails_on_trivially_different_but_same_context():
    # ...but incorrectly scores a trivial diff (same real context) as
    # wrong — this is exactly the failure mode semantic detection fixes.
    pairs = [{"title_a": "main.py - line 42", "title_b": "main.py - line 43", "same_context": "1"}]
    assert naive_baseline_accuracy(pairs) == 0.0


def test_semantic_accuracy_computed_correctly_with_fake_provider():
    pairs = [
        {"title_a": "a", "title_b": "a", "same_context": "1"},  # identical -> same, correct
    ]
    detector = SemanticChangeDetector(FakeEmbeddingProvider(), threshold=0.75)
    assert semantic_accuracy(pairs, detector) == 1.0