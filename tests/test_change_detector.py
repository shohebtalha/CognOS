from cogn_os.embeddings.change_detector import SemanticChangeDetector
from cogn_os.embeddings.fake_provider import FakeEmbeddingProvider


class FixedSimilarityProvider(FakeEmbeddingProvider):
    """Test helper: returns hand-picked vectors so cosine similarity
    between two specific texts is exactly controllable, rather than
    relying on the fake provider's hash-based randomness."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        super().__init__(dimension=len(next(iter(vectors.values()))))
        self._vectors = vectors

    def embed(self, text: str):
        import numpy as np
        self.call_count += 1
        self.received_texts.append(text)
        return np.array(self._vectors[text], dtype="float32")


def test_first_title_is_always_a_change():
    detector = SemanticChangeDetector(FakeEmbeddingProvider())
    decision = detector.compare(previous_title=None, current_title="main.py")
    assert decision.is_different is True


def test_identical_titles_short_circuit_without_embedding():
    provider = FakeEmbeddingProvider()
    detector = SemanticChangeDetector(provider)

    decision = detector.compare(previous_title="main.py", current_title="main.py")

    assert decision.is_different is False
    assert decision.similarity == 1.0
    assert provider.call_count == 0  # never called embed() — short-circuited


def test_highly_similar_titles_are_not_flagged_as_different():
    provider = FixedSimilarityProvider({
        "main.py - line 42": [1.0, 0.0, 0.0],
        "main.py - line 43": [0.99, 0.01, 0.0],  # nearly identical direction
    })
    detector = SemanticChangeDetector(provider, threshold=0.75)

    decision = detector.compare("main.py - line 42", "main.py - line 43")

    assert decision.is_different is False
    assert decision.similarity > 0.75


def test_dissimilar_titles_are_flagged_as_different():
    provider = FixedSimilarityProvider({
        "main.py - CognOS": [1.0, 0.0, 0.0],
        "Stack Overflow - segfault": [0.0, 1.0, 0.0],  # orthogonal
    })
    detector = SemanticChangeDetector(provider, threshold=0.75)

    decision = detector.compare("main.py - CognOS", "Stack Overflow - segfault")

    assert decision.is_different is True
    assert decision.similarity < 0.75


def test_threshold_is_configurable():
    provider = FixedSimilarityProvider({
        "a": [1.0, 0.0],
        "b": [0.8, 0.6],  # similarity = 0.8
    })

    lenient = SemanticChangeDetector(provider, threshold=0.5)
    strict = SemanticChangeDetector(provider, threshold=0.9)

    assert lenient.compare("a", "b").is_different is False  # 0.8 > 0.5, not different
    assert strict.compare("a", "b").is_different is True    # 0.8 < 0.9, different


def test_decision_reports_the_threshold_used():
    provider = FakeEmbeddingProvider()
    detector = SemanticChangeDetector(provider, threshold=0.6)
    decision = detector.compare("a", "b")
    assert decision.threshold == 0.6