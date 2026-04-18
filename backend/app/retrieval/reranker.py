"""Reranker：优先 Cohere rerank-v3.5，回退 BGE-reranker-v2-m3。"""
from __future__ import annotations

from functools import lru_cache

from loguru import logger

from app.core.config import get_settings


class Reranker:
    def __init__(self) -> None:
        self.s = get_settings()

    async def rerank(self, query: str, docs: list[dict], top_k: int = 8) -> list[dict]:
        if not docs:
            return []
        if self.s.cohere_api_key:
            return await self._cohere(query, docs, top_k)
        return await self._bge(query, docs, top_k)

    async def _cohere(self, query, docs, top_k):
        import cohere
        co = cohere.AsyncClient(self.s.cohere_api_key)
        res = await co.rerank(model=self.s.rerank_model, query=query,
                              documents=[d["text"] for d in docs], top_n=top_k)
        out = []
        for r in res.results:
            d = dict(docs[r.index])
            d["rerank_score"] = r.relevance_score
            out.append(d)
        return out

    async def _bge(self, query, docs, top_k):
        from FlagEmbedding import FlagReranker
        model = _get_bge()
        pairs = [[query, d["text"]] for d in docs]
        scores = model.compute_score(pairs, normalize=True)
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [{**d, "rerank_score": float(s)} for d, s in ranked]


@lru_cache
def _get_bge():
    from FlagEmbedding import FlagReranker
    return FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
