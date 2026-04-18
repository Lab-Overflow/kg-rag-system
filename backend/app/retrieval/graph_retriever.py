"""图检索：
 1) 实体链接（向量 + 别名匹配）
 2) 1-2 hop 子图抽取
 3) HippoRAG 2：PPR 排序实体 → 回写 chunk 证据
 4) GraphRAG global：社区摘要 → map-reduce
"""
from __future__ import annotations

from loguru import logger

from app.kg.neo4j_client import Neo4jClient
from app.retrieval.embedder import get_embedder


async def link_entities(tenant: str, query: str, limit: int = 8) -> list[dict]:
    emb = (await get_embedder().embed_texts([query]))[0]
    kg = Neo4jClient()
    async with kg._driver.session() as sess:
        res = await sess.run("""
        CALL db.index.vector.queryNodes('entity_embedding', $k, $emb)
        YIELD node, score
        WHERE node.tenant = $tenant
        RETURN node.id AS id, node.name AS name, node.type AS type, score
        """, k=limit, emb=emb, tenant=tenant)
        rows = [dict(r) async for r in res]
    await kg.close()
    return rows


async def local_subgraph_context(tenant: str, query: str) -> dict:
    """实体链接 + 邻域关系 + 邻域 chunk 证据。"""
    seeds = await link_entities(tenant, query)
    kg = Neo4jClient()
    sub = await kg.subgraph(tenant=tenant, seed=None, hops=2, limit=200) if not seeds \
        else await kg.subgraph(tenant=tenant, seed=seeds[0]["id"], hops=2, limit=200)
    await kg.close()
    return {"seeds": seeds, "subgraph": sub}


async def hippo_retrieve(tenant: str, query: str, k: int = 30) -> list[dict]:
    seeds = await link_entities(tenant, query, limit=5)
    if not seeds:
        return []
    kg = Neo4jClient()
    ranked = await kg.personalized_pagerank(tenant, [s["id"] for s in seeds], top_k=k)
    await kg.close()
    return ranked


async def global_summaries(tenant: str, level: int = 0, top: int = 8) -> list[dict]:
    kg = Neo4jClient()
    comms = await kg.list_communities(tenant)
    await kg.close()
    comms.sort(key=lambda c: c.get("size", 0), reverse=True)
    return comms[:top]
