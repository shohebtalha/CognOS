import numpy as np

from cogn_os.embeddings.fake_provider import FakeEmbeddingProvider


def test_same_text_returns_same_vector():
    provider = FakeEmbeddingProvider()
    v1 = provider.embed("hello")
    v2 = provider.embed("hello")
    assert np.array_equal(v1, v2)


def test_different_text_returns_different_vector():
    provider = FakeEmbeddingProvider()
    v1 = provider.embed("hello")
    v2 = provider.embed("goodbye")
    assert not np.array_equal(v1, v2)


def test_dimension_is_configurable():
    provider = FakeEmbeddingProvider(dimension=16)
    v = provider.embed("x")
    assert v.shape == (16,)
    assert provider.dimension == 16


def test_tracks_call_count_and_received_texts():
    provider = FakeEmbeddingProvider()
    provider.embed("a")
    provider.embed("b")
    assert provider.call_count == 2
    assert provider.received_texts == ["a", "b"]