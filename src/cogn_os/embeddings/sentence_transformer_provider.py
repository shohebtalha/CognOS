"""
Real EmbeddingProvider backed by sentence-transformers (PyTorch under
the hood), running entirely locally — no network call, no API key,
genuine local inference. Model chosen: all-MiniLM-L6-v2, a small
(~90MB), fast, well-established sentence embedding model — 384-dim
output, good enough quality for short window-title strings without the
latency/memory cost of a larger model. This is a deliberate size/quality
tradeoff, not the "best available" model, and that tradeoff is the kind
of thing worth being able to explain if asked.

The model is loaded once at construction (expensive: disk read + model
init) and reused for every embed() call — never reloaded per-call.
"""

from __future__ import annotations

import logging

import numpy as np

from cogn_os.embeddings.types import EmbeddingProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_DIMENSION = 384


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "pip install sentence-transformers torch"
            ) from e

        logger.info("loading local embedding model: %s (first run downloads it)", model_name)
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> np.ndarray:
        # encode() on a single string still returns a batch internally;
        # convert_to_numpy keeps this method's return type consistent
        # with the interface contract regardless of torch tensor internals.
        vector = self._model.encode(text, convert_to_numpy=True)
        return vector.astype(np.float32)

    @property
    def dimension(self) -> int:
        return self._dimension