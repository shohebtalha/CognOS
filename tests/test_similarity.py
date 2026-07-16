import numpy as np
import pytest
from cogn_os.embeddings.similarity import cosine_similarity


def test_identical_vectors_have_similarity_1():
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_orthogonal_vectors_have_similarity_0():
    v1 = np.array([1.0, 0.0])
    v2 = np.array([0.0, 1.0])
    assert cosine_similarity(v1, v2) == pytest.approx(0.0)


def test_opposite_vectors_have_similarity_negative_1():
    v1 = np.array([1.0, 0.0])
    v2 = np.array([-1.0, 0.0])
    assert cosine_similarity(v1, v2) == pytest.approx(-1.0)


def test_zero_vector_returns_0_without_crashing():
    v1 = np.array([0.0, 0.0])
    v2 = np.array([1.0, 1.0])
    assert cosine_similarity(v1, v2) == 0.0


def test_similarity_is_scale_invariant():
    v1 = np.array([1.0, 2.0, 3.0])
    v2 = np.array([2.0, 4.0, 6.0])  # same direction, different magnitude
    assert cosine_similarity(v1, v2) == pytest.approx(1.0)