"""Exact MiniLM embedding search for NeMo's small internal flow indexes.

NeMo 0.10 defaults to Annoy, which needs a native Windows compiler. This
implements NeMo's EmbeddingsIndex interface with the same local MiniLM model
and exact cosine ranking. It changes flow search only; input/output self-check
LLM calls remain NeMo's own rails.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Optional

import numpy as np
from nemoguardrails.embeddings.index import EmbeddingsIndex, IndexItem


@lru_cache(maxsize=1)
def _model():
    # Torch must be loaded before SentenceTransformers on this Windows runtime.
    import torch  # noqa: F401
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2",
                               local_files_only=True)


def warm_model() -> None:
    """Load once before NeMo starts its concurrent index-initialization thread."""
    _model()


class ExactMiniLMIndex(EmbeddingsIndex):
    def __init__(self):
        self._items: list[IndexItem] = []
        self._vectors = np.empty((0, 384), dtype=np.float32)

    @property
    def embedding_size(self) -> int:
        return self._vectors.shape[1]

    @property
    def cache_config(self):
        return None

    async def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return _model().encode(texts, normalize_embeddings=True,
                               convert_to_numpy=True).tolist()

    async def add_item(self, item: IndexItem) -> None:
        await self.add_items([item])

    async def add_items(self, items: list[IndexItem]) -> None:
        if not items:
            return
        vectors = np.asarray(await self._get_embeddings([item.text for item in items]),
                             dtype=np.float32)
        self._items.extend(items)
        self._vectors = np.concatenate((self._vectors, vectors), axis=0)

    async def build(self) -> None:
        if not self._items:
            raise ValueError("Cannot build an empty NeMo flow index")

    async def search(self, text: str, max_results: int = 20,
                     threshold: Optional[float] = None) -> list[IndexItem]:
        if max_results <= 0 or not self._items:
            return []
        query = np.asarray((await self._get_embeddings([text]))[0], dtype=np.float32)
        cosine = self._vectors @ query
        indices = np.argsort(-cosine, kind="stable")[:max_results]
        if threshold is None or threshold == float("inf"):
            return [self._items[index] for index in indices]
        # Match BasicEmbeddingsIndex: score = 1 - angular_distance / 2.
        return [self._items[index] for index in indices
                if 1 - math.sqrt(max(0.0, 2 - 2 * float(cosine[index]))) / 2 >= threshold]
