"""Agent 可调用的工具。也被 MCP server 复用。"""
from __future__ import annotations

from pydantic import BaseModel


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict


async def kg_query(q: str, mode: str = "hybrid", top_k: int = 8) -> dict:
    from app.core.security import Principal
    from app.models.schemas import QueryRequest, RetrievalMode
    from app.retrieval.router import RetrievalRouter
    router = RetrievalRouter()
    req = QueryRequest(q=q, mode=RetrievalMode(mode), top_k=top_k)
    res = await router.run(req, Principal(tenant="default", user_id="tool"))
    return res.model_dump()


async def kg_subgraph(seed: str, hops: int = 2, limit: int = 200) -> dict:
    from app.kg.neo4j_client import Neo4jClient
    kg = Neo4jClient()
    out = await kg.subgraph("default", seed=seed, hops=hops, limit=limit)
    await kg.close()
    return out


async def kg_entity_search(name: str, k: int = 10) -> list[dict]:
    from app.retrieval.graph_retriever import link_entities
    return await link_entities("default", name, limit=k)
