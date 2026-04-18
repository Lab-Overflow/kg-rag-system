"""Qdrant 多向量 collection：
  named vectors: dense (cosine) + sparse (dot)
  payload: tenant, doc_id, chunk_id, text, meta
  量化：scalar int8，节省 4×
"""
from __future__ import annotations

from typing import Any

from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from app.core.config import get_settings
from app.models.schemas import Chunk


class QdrantStore:
    COLLECTION = "kg_rag_chunks"

    def __init__(self, tenant: str) -> None:
        self.tenant = tenant
        self.client = AsyncQdrantClient(url=get_settings().qdrant_url, timeout=30)

    async def ensure(self) -> None:
        cols = await self.client.get_collections()
        if any(c.name == self.COLLECTION for c in cols.collections):
            return
        await self.client.create_collection(
            collection_name=self.COLLECTION,
            vectors_config={
                "dense": qm.VectorParams(size=1024, distance=qm.Distance.COSINE,
                                         on_disk=True,
                                         quantization_config=qm.ScalarQuantization(
                                             scalar=qm.ScalarQuantizationConfig(
                                                 type=qm.ScalarType.INT8, always_ram=True)
                                         )),
            },
            sparse_vectors_config={
                "sparse": qm.SparseVectorParams(index=qm.SparseIndexParams(on_disk=False)),
            },
            optimizers_config=qm.OptimizersConfigDiff(default_segment_number=4),
        )
        await self.client.create_payload_index(self.COLLECTION, field_name="tenant",
                                               field_schema="keyword")
        await self.client.create_payload_index(self.COLLECTION, field_name="doc_id",
                                               field_schema="keyword")
        logger.info("qdrant collection ready")

    async def upsert_chunks(self, chunks: list[Chunk], embedder) -> None:
        await self.ensure()
        vecs = await embedder.embed_with_sparse([c.text for c in chunks])
        points = []
        for c, d, s in zip(chunks, vecs["dense"], vecs["sparse"]):
            points.append(qm.PointStruct(
                id=c.id, payload={"tenant": self.tenant, "doc_id": c.doc_id,
                                  "chunk_id": c.id, "text": c.text,
                                  "order": c.order, "meta": c.meta},
                vector={"dense": d,
                        "sparse": qm.SparseVector(indices=s["indices"], values=s["values"])},
            ))
        for i in range(0, len(points), 256):
            await self.client.upsert(self.COLLECTION, points=points[i:i + 256])

    async def search_hybrid(
        self, query: str, embedder, top_k: int = 20,
    ) -> list[dict[str, Any]]:
        await self.ensure()
        vecs = await embedder.embed_with_sparse([query])
        tenant_filter = qm.Filter(must=[qm.FieldCondition(key="tenant",
                                                          match=qm.MatchValue(value=self.tenant))])
        res = await self.client.query_points(
            collection_name=self.COLLECTION,
            prefetch=[
                qm.Prefetch(query=vecs["dense"][0], using="dense", limit=top_k * 3,
                            filter=tenant_filter),
                qm.Prefetch(query=qm.SparseVector(indices=vecs["sparse"][0]["indices"],
                                                  values=vecs["sparse"][0]["values"]),
                            using="sparse", limit=top_k * 3, filter=tenant_filter),
            ],
            query=qm.FusionQuery(fusion=qm.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        return [{"id": p.id, "score": p.score, **p.payload} for p in res.points]
