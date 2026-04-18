"""Retrieval Router：按 mode 分发；并为 agentic 模式提供入口。"""
from __future__ import annotations

from loguru import logger

from app.core.config import get_settings
from app.core.security import Principal
from app.models.schemas import (
    Citation, QueryRequest, QueryResponse, RetrievalMode, SubgraphPayload,
)
from app.retrieval.embedder import get_embedder
from app.retrieval.graph_retriever import (
    global_summaries, hippo_retrieve, local_subgraph_context,
)
from app.retrieval.qdrant_store import QdrantStore
from app.retrieval.reranker import Reranker


class RetrievalRouter:
    def __init__(self) -> None:
        self.reranker = Reranker()

    async def run(self, req: QueryRequest, principal: Principal) -> QueryResponse:
        tenant = req.tenant or principal.tenant
        mode = req.mode
        if mode == RetrievalMode.hybrid or mode == RetrievalMode.naive:
            return await self._hybrid(req, tenant, mode)
        if mode == RetrievalMode.local_graph:
            return await self._local(req, tenant)
        if mode == RetrievalMode.global_graph:
            return await self._global(req, tenant)
        if mode == RetrievalMode.hippo:
            return await self._hippo(req, tenant)
        if mode == RetrievalMode.colpali:
            return await self._colpali(req, tenant)
        raise ValueError(f"unsupported mode {mode}")

    async def agentic(self, req: QueryRequest, principal: Principal) -> QueryResponse:
        from app.agents.graph_agent import run_agent
        return await run_agent(req, principal, self)

    # ------------- strategies ----------------
    async def _hybrid(self, req, tenant, mode):
        store = QdrantStore(tenant=tenant)
        hits = await store.search_hybrid(req.q, get_embedder(), top_k=req.top_k)
        reranked = await self.reranker.rerank(req.q, hits, top_k=get_settings().rerank_top_k)
        cites = [self._to_citation(h) for h in reranked]
        answer = await self._synthesize(req.q, cites)
        return QueryResponse(answer=answer, citations=cites, mode_used=mode)

    async def _local(self, req, tenant):
        ctx = await local_subgraph_context(tenant, req.q)
        # 也拉一把 hybrid 文本证据
        hits = await QdrantStore(tenant=tenant).search_hybrid(req.q, get_embedder(),
                                                              top_k=req.top_k)
        reranked = await self.reranker.rerank(req.q, hits, top_k=8)
        cites = [self._to_citation(h) for h in reranked]
        answer = await self._synthesize(req.q, cites, graph_context=ctx)
        return QueryResponse(
            answer=answer, citations=cites,
            subgraph=SubgraphPayload(**ctx["subgraph"]),
            mode_used=RetrievalMode.local_graph,
        )

    async def _global(self, req, tenant):
        comms = await global_summaries(tenant, top=10)
        # map: 每社区摘要对问题做子答案；reduce：合成
        from app.agents.planner import map_reduce_over_communities
        answer = await map_reduce_over_communities(req.q, comms)
        return QueryResponse(answer=answer, citations=[], mode_used=RetrievalMode.global_graph)

    async def _hippo(self, req, tenant):
        ranked = await hippo_retrieve(tenant, req.q, k=30)
        # 回到 chunk 证据：对每个 top entity，抓其 evidence chunk
        from app.kg.neo4j_client import Neo4jClient
        kg = Neo4jClient()
        ids = [r["id"] for r in ranked[:12]]
        chunks = []
        if ids:
            async with kg._driver.session() as sess:
                res = await sess.run("""
                MATCH (e:Entity)-[r:REL]-()
                WHERE e.id IN $ids
                UNWIND r.evidence AS cid
                RETURN DISTINCT cid LIMIT 40
                """, ids=ids)
                chunks = [r["cid"] async for r in res]
        await kg.close()
        # 用 chunk id 查 qdrant payload
        store = QdrantStore(tenant=tenant)
        await store.ensure()
        from qdrant_client.http import models as qm
        pts = await store.client.retrieve(
            collection_name=QdrantStore.COLLECTION,
            ids=chunks or [],
            with_payload=True,
        )
        hits = [{"id": p.id, "score": 1.0, **p.payload} for p in pts]
        reranked = await self.reranker.rerank(req.q, hits, top_k=8)
        cites = [self._to_citation(h) for h in reranked]
        answer = await self._synthesize(req.q, cites)
        return QueryResponse(answer=answer, citations=cites, mode_used=RetrievalMode.hippo)

    async def _colpali(self, req, tenant):
        # 占位：把查询 embed 成 ColPali，搜 image-patch collection
        return QueryResponse(
            answer="ColPali multimodal retrieval placeholder",
            citations=[], mode_used=RetrievalMode.colpali,
        )

    # ------------- helpers -------------------
    def _to_citation(self, h: dict) -> Citation:
        return Citation(
            chunk_id=h.get("chunk_id", h["id"]),
            doc_id=h.get("doc_id", ""),
            score=float(h.get("rerank_score", h.get("score", 0.0))),
            snippet=(h.get("text") or "")[:400],
            source=(h.get("meta") or {}).get("source", ""),
        )

    async def _synthesize(self, q: str, cites: list[Citation], graph_context: dict | None = None):
        from anthropic import AsyncAnthropic
        s = get_settings()
        client = AsyncAnthropic(api_key=s.anthropic_api_key)
        ctx = "\n\n".join(f"[{i+1}] ({c.source}) {c.snippet}" for i, c in enumerate(cites))
        graph_text = ""
        if graph_context:
            g = graph_context.get("subgraph", {})
            graph_text = "\nGraph context (nodes/edges):\n" + str(g)[:1500]
        prompt = (
            "Answer the question using ONLY the provided context. Cite like [1][2]. "
            "If evidence is insufficient, say so.\n\n"
            f"Question: {q}\n\nContext:\n{ctx}{graph_text}"
        )
        try:
            msg = await client.messages.create(
                model=s.llm_synthesizer, max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in msg.content if hasattr(b, "text"))
        except Exception as e:
            logger.warning(f"synthesize failed: {e}")
            return "(synthesis failed — please check LLM credentials)"
