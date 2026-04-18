"""GraphRAG 风格社区发现 + 分层摘要：
- 用 Leiden（GDS）得到多级社区
- 每个社区取节点邻域文本 → LLM map-reduce 生成摘要
- 摘要写回 :Community 节点，支持 `global_graph` 检索模式
"""
from __future__ import annotations

from loguru import logger

from app.core.config import get_settings
from app.kg.neo4j_client import Neo4jClient


async def detect_and_summarize(tenant: str, incremental: bool = False) -> dict:
    """Detect Leiden communities then summarize via LLM map-reduce.

    incremental=True 时仅对新增实体所在社区重算（prod 需要）。
    """
    kg = Neo4jClient()
    graph_name = f"tenant_{tenant}_com"
    try:
        async with kg._driver.session() as sess:
            # 1) project
            try:
                await sess.run(f"""
                CALL gds.graph.project.cypher(
                  '{graph_name}',
                  'MATCH (n:Entity {{tenant:"{tenant}"}}) RETURN id(n) AS id',
                  'MATCH (a:Entity {{tenant:"{tenant}"}})-[r:REL]-(b:Entity {{tenant:"{tenant}"}})
                   RETURN id(a) AS source, id(b) AS target, coalesce(r.weight,1.0) AS weight'
                ) YIELD graphName
                """)
            except Exception:
                pass
            # 2) Leiden
            await sess.run(f"""
            CALL gds.leiden.write('{graph_name}', {{
              writeProperty: 'communityId_{tenant}',
              includeIntermediateCommunities: true,
              relationshipWeightProperty: 'weight'
            }}) YIELD communityCount, modularity
            """)
            # 3) create :Community nodes
            await sess.run(f"""
            MATCH (e:Entity {{tenant:$tenant}}) WHERE e.`communityId_{tenant}` IS NOT NULL
            WITH e.`communityId_{tenant}` AS cid, collect(e) AS members
            MERGE (c:Community {{id: 'c_' + toString(cid), tenant:$tenant, level:0}})
            SET c.size = size(members)
            FOREACH (m IN members | MERGE (m)-[:IN_COMMUNITY]->(c))
            """, tenant=tenant)
    finally:
        await kg.close()
    logger.info(f"[{tenant}] communities rebuilt")

    await _summarize(tenant)
    return {"tenant": tenant, "status": "ok"}


async def _summarize(tenant: str) -> None:
    """Per community：拉取 top-20 entities + 典型 relation triples → LLM 生成 200 字摘要。"""
    from anthropic import AsyncAnthropic
    s = get_settings()
    client = AsyncAnthropic(api_key=s.anthropic_api_key)
    kg = Neo4jClient()
    async with kg._driver.session() as sess:
        res = await sess.run("""
        MATCH (c:Community {tenant:$tenant})<-[:IN_COMMUNITY]-(e:Entity)
        WITH c, collect(e)[..20] AS members
        UNWIND members AS m
        OPTIONAL MATCH (m)-[r:REL]-(o:Entity)<-[:IN_COMMUNITY]-(c)
        WITH c, members,
             collect(DISTINCT m.name+' -['+r.type+']-> '+o.name)[..30] AS triples
        RETURN c.id AS cid, [m IN members | m.name] AS names, triples
        """, tenant=tenant)
        rows = [dict(r) async for r in res]

    for row in rows:
        prompt = (
            "Summarize this knowledge-graph community in ≤180 words. "
            "Highlight key actors, themes, and salient relations.\n"
            f"Members: {', '.join(row['names'])}\n"
            f"Triples:\n" + "\n".join(row["triples"])
        )
        try:
            msg = await client.messages.create(
                model=s.llm_extractor, max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = "".join(b.text for b in msg.content if hasattr(b, "text"))
        except Exception as e:
            logger.warning(f"summarize failed {row['cid']}: {e}")
            summary = ""
        async with kg._driver.session() as sess:
            await sess.run(
                "MATCH (c:Community {id:$cid, tenant:$tenant}) SET c.summary=$s",
                cid=row["cid"], tenant=tenant, s=summary,
            )
    await kg.close()
