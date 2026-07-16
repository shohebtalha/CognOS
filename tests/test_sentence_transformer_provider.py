"""
Runs against the REAL local model — deliberately, since this is the one
place proving actual PyTorch inference works end-to-end, not mocked.
First run will download the model (~90MB) and may take a minute;
subsequent runs use the cached model and are fast.
"""

from __future__ import annotations

import numpy as np
import pytest

from cogn_os.embeddings.sentence_transformer_provider import SentenceTransformerProvider


@pytest.fixture(scope="module")
def provider():
    return SentenceTransformerProvider()


def test_embed_returns_correct_dimension(provider):
    vector = provider.embed("main.py - Visual Studio Code")
    assert vector.shape == (provider.dimension,)
    assert provider.dimension == 384


def test_embed_returns_float32(provider):
    vector = provider.embed("some text")
    assert vector.dtype == np.float32


def test_similar_titles_produce_similar_embeddings(provider):
    v1 = provider.embed("main.py - Visual Studio Code")
    v2 = provider.embed("utils.py - Visual Studio Code")
    v3 = provider.embed("Inbox - Gmail")

    cos_sim_similar = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    cos_sim_different = np.dot(v1, v3) / (np.linalg.norm(v1) * np.linalg.norm(v3))

    # Two code-editor titles should be more semantically similar to each
    # other than either is to an unrelated email inbox title — this is
    # the actual behavior the whole embeddings phase depends on.
    assert cos_sim_similar > cos_sim_different


def test_identical_text_produces_identical_embedding(provider):
    v1 = provider.embed("same text")
    v2 = provider.embed("same text")
    assert np.array_equal(v1, v2)


def test_empty_string_does_not_crash(provider):
    vector = provider.embed("")
    assert vector.shape == (provider.dimension,)