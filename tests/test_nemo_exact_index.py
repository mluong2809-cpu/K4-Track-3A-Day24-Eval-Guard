"""Offline check for the native-Annoy-free NeMo flow index."""

import asyncio

import numpy as np
import pytest

pytest.importorskip("nemoguardrails")

from nemoguardrails.embeddings.index import IndexItem
from src import nemo_exact_index


def test_exact_index_ranks_by_cosine_without_network(monkeypatch):
    class FixedModel:
        def encode(self, texts, **kwargs):
            vectors = {"leave": [1.0, 0.0], "password": [0.0, 1.0],
                       "password query": [0.0, 1.0]}
            return np.asarray([vectors[text] for text in texts], dtype=np.float32)

    monkeypatch.setattr(nemo_exact_index, "_model", lambda: FixedModel())

    async def run():
        index = nemo_exact_index.ExactMiniLMIndex()
        await index.add_items([IndexItem("leave"), IndexItem("password")])
        await index.build()
        return await index.search("password query", max_results=1)

    assert [item.text for item in asyncio.run(run())] == ["password"]
