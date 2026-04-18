"""Neo4j 客户端：写实体/关系、子图查询、PPR、社区查询。"""
from __future__ import annotations

from typing import Any

from loguru import logger
from neo4j import AsyncGraphDatabase

from app.core.config import get_settings
from app.models.schemas import ExtractionResult


class Neo4jClient:
    def __init__(self) -> None:
        s = get_settings()
        self._driver = AsyncGraphDatabase.driver(
            s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password), max_connection_pool_size=50,
        )

    async def close(self) -> None:
        await self._driver.close()

    # ------------ schema & constraints -------------
    async def init_schema(self) -> None:
        stmts = [
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE INDEX entity_tenant IF NOT EXISTS FOR (e:Entity) ON (e.tenant)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            # vector index on entity description embedding
            """
            CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
            FOR (e:Entity) ON (e.embedding)
            OPTIONS { indexConfig: { `vector.dimensions`: 1024, `vector.similarity_function`: 'cosine' }}
            """,
        ]
        async with self._driver.session() as sess:
            for s in stmts:
                try:
                    await sess.run(s)
                except Exception as e:  # pragma: no cover
                    logger.warning(f"schema stmt failed: {e}")

    # ------------ write ---------------------------
    async def write_extraction(
        self, tenant: str, doc_id: str, ex: ExtractionResult, embedder,
    ) -> None:
        # embed entity descriptions for vector index
        texts = [f"{e.name} ({e.type}): {e.description or ''}" for e in ex.entities]
        embs = await embedder.embed_texts(texts) if texts else []
        ent_rows = [
            {
                "id": e.id, "name": e.name, "type": e.type,
                "aliases": e.aliases, "description": e.description,
                "embedding": embs[i] if embs else None, "tenant": tenant,
            }
            for i, e in enumerate(ex.entities)
        ]
        rel_rows = [
            {
                "head": r.head, "tail": r.tail, "type": r.type,
                "weight": r.weight, "evidence": r.evidence,
                "confidence": r.confidence, "tenant": tenant, "doc_id": doc_id,
            }
            for r in ex.relations
        ]
        async with self._driver.session() as sess:
            await sess.run(
                """
                UNWIND $rows AS row
                MERGE (e:Entity {id: row.id})
                SET  e.name=row.name, e.type=row.type, e.tenant=row.tenant,
                     e.aliases=row.aliases, e.description=row.description,
                     e.embedding=row.embedding
                """,
                rows=ent_rows,
            )
            await sess.run(
                """
                UNWIND $rows AS row
                MATCH (h:Entity {id: row.head}), (t:Entity {id: row.tail})
                MERGE (h)-[r:REL {type: row.type}]->(t)
                SET  r.weight   = coalesce(r.weight,0)   + row.weight,
                     r.confidence = row.confidence,
                     r.tenant   = row.tenant,
                     r.evidence = coalesce(r.evidence,[]) + row.evidence,
                     r.doc_ids  = coalesce(r.doc_ids,[]) + [row.doc_id]
                """,
                rows=rel_rows,
            )

    # ------------ subgraph -----------------------
    async def subgraph(
        self, tenant: str, seed: str | None, hops: int = 2,
        limit: int = 300, min_confidence: float = 0.0,
    ) -> dict[str, Any]:
        cypher = """
        MATCH (e:Entity {tenant:$tenant})
        WHERE $seed IS NULL OR e.name CONTAINS $seed OR e.id = $seed
        WITH e LIMIT 20
        CALL apoc.path.subgraphAll(e, {maxLevel:$hops, relationshipFilter:'REL'}) YIELD nodes, relationships
        WITH nodes, [r IN relationships WHERE r.confidence >= $min_conf] AS rels
        RETURN [n IN nodes | {id:n.id, name:n.name, type:n.type}] AS nodes,
               [r IN rels  | {source:startNode(r).id, target:endNode(r).id,
                              type:r.type, weight:r.weight}] AS edges
        LIMIT $limit
        """
        async with self._driver.session() as sess:
            rec = await (await sess.run(cypher, tenant=tenant, seed=seed,
                                        hops=hops, min_conf=min_confidence, limit=limit)).single()
            if rec is None:
                return {"nodes": [], "edges": []}
            return {"nodes": rec["nodes"], "edges": rec["edges"]}

    # ------------ PPR (HippoRAG 2) ----------------
    async def personalized_pagerank(
        self, tenant: str, seed_ids: list[str], top_k: int = 30,
    ) -> list[dict[str, Any]]:
        """Run PPR via GDS with source nodes = seed entities."""
        graph_name = f"tenant_{tenant}_pg"
        cypher_project = f"""
        CALL gds.graph.project.cypher(
          '{graph_name}',
          'MATCH (n:Entity {{tenant:"{tenant}"}}) RETURN id(n) AS id',
          'MATCH (a:Entity {{tenant:"{tenant}"}})-[r:REL]-(b:Entity {{tenant:"{tenant}"}})
           RETURN id(a) AS source, id(b) AS target, coalesce(r.weight,1.0) AS weight'
        ) YIELD graphName
        """
        cypher_ppr = f"""
        MATCH (seed:Entity) WHERE seed.id IN $seeds
        WITH collect(seed) AS seeds
        CALL gds.pageRank.stream('{graph_name}', {{sourceNodes: seeds, relationshipWeightProperty:'weight'}})
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId) AS n, score
        ORDER BY score DESC LIMIT $k
        """
        cypher_drop = f"CALL gds.graph.drop('{graph_name}', false)"
        async with self._driver.session() as sess:
            try:
                await sess.run(cypher_project)
            except Exception:
                pass  # already projected
            res = await sess.run(cypher_ppr, seeds=seed_ids, k=top_k)
            rows = [{"id": r["n"]["id"], "name": r["n"]["name"], "score": r["score"]}
                    async for r in res]
            await sess.run(cypher_drop)
        return rows

    async def list_communities(self, tenant: str) -> list[dict[str, Any]]:
        cypher = """
        MATCH (c:Community {tenant:$tenant})
        RETURN c.id AS id, c.level AS level, c.summary AS summary, c.size AS size
        ORDER BY c.level, c.size DESC LIMIT 500
        """
        async with self._driver.session() as sess:
            res = await sess.run(cypher, tenant=tenant)
            return [dict(r) async for r in res]

    async def stats(self, tenant: str) -> dict[str, Any]:
        cypher = """
        MATCH (e:Entity {tenant:$tenant}) WITH count(e) AS ents
        MATCH ()-[r:REL {tenant:$tenant}]->() RETURN ents, count(r) AS rels
        """
        async with self._driver.session() as sess:
            rec = await (await sess.run(cypher, tenant=tenant)).single()
            return dict(rec) if rec else {"ents": 0, "rels": 0}
