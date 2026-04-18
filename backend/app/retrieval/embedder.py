"""统一 Embedder：
 - dense: BGE-M3
 - sparse: SPLADE
 - 多进程池可扩展（留接口）
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np


class Embedder:
    def __init__(self) -> None:
        from FlagEmbedding import BGEM3FlagModel
        self._dense = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out = self._dense.encode(texts, batch_size=32, return_dense=True,
                                 return_sparse=False, return_colbert_vecs=False)
        return [v.tolist() for v in out["dense_vecs"]]

    async def embed_with_sparse(self, texts: list[str]) -> dict:
        out = self._dense.encode(texts, batch_size=32, return_dense=True,
                                 return_sparse=True, return_colbert_vecs=False)
        return {
            "dense": [v.tolist() for v in out["dense_vecs"]],
            "sparse": [
                {"indices": list(d.keys()), "values": [float(x) for x in d.values()]}
                for d in out["lexical_weights"]
            ],
        }


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()
