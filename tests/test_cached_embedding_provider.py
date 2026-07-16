from cogn_os.embeddings.cached_provider import CachedEmbeddingProvider
from cogn_os.embeddings.fake_provider import FakeEmbeddingProvider
import pytest


def test_repeated_text_hits_cache_not_inner_provider():
    inner = FakeEmbeddingProvider()
    cached = CachedEmbeddingProvider(inner)

    cached.embed("same title")
    cached.embed("same title")
    cached.embed("same title")

    assert inner.call_count == 1  # only embedded once, rest served from cache
    assert cached.cache_hits == 2
    assert cached.cache_misses == 1


def test_different_texts_each_miss_the_cache():
    inner = FakeEmbeddingProvider()
    cached = CachedEmbeddingProvider(inner)

    cached.embed("a")
    cached.embed("b")
    cached.embed("c")

    assert inner.call_count == 3
    assert cached.cache_misses == 3
    assert cached.cache_hits == 0


def test_returns_same_vector_as_inner_provider_would():
    inner = FakeEmbeddingProvider()
    cached = CachedEmbeddingProvider(inner)

    direct = inner.embed("check consistency")
    cached_result = cached.embed("check consistency")

    import numpy as np
    assert np.array_equal(direct, cached_result)


def test_dimension_delegates_to_inner_provider():
    inner = FakeEmbeddingProvider(dimension=16)
    cached = CachedEmbeddingProvider(inner)
    assert cached.dimension == 16


def test_eviction_when_max_size_exceeded():
    inner = FakeEmbeddingProvider()
    cached = CachedEmbeddingProvider(inner, max_size=2)

    cached.embed("a")
    cached.embed("b")
    cached.embed("c")  # should evict "a" (least recently used)

    cached.embed("a")  # must miss again since it was evicted
    assert inner.call_count == 4  # a, b, c, then a again


def test_hit_rate_calculation():
    inner = FakeEmbeddingProvider()
    cached = CachedEmbeddingProvider(inner)

    cached.embed("x")       # miss
    cached.embed("x")       # hit
    cached.embed("x")       # hit

    assert cached.hit_rate == pytest.approx(2 / 3)


def test_hit_rate_is_zero_with_no_calls():
    inner = FakeEmbeddingProvider()
    cached = CachedEmbeddingProvider(inner)
    assert cached.hit_rate == 0.0