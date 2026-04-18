"""Ingestion pipeline orchestrator:
 load -> chunk -> embed -> KG extract -> write -> community update

Demo 实现单机异步；生产切 Ray Actor pool（占位已留）。
"""
from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from loguru import logger

from app.core.config import get_settings
from app.ingestion.chunker import chunk_text, new_doc_id
from app.ingestion.extractor import extract
from app.ingestion.loaders import load
from app.kg.neo4j_client import Neo4jClient
from app.kg.community import detect_and_summarize
from app.models.schemas import IngestJob, IngestStatus
from app.retrieval.embedder import Embedder
from app.retrieval.qdrant_store import QdrantStore

_JOBS: dict[str, IngestJob] = {}


async def run_ingest_job(job: IngestJob, filename: str, blob: bytes) -> None:
    _JOBS[job.job_id] = job
    try:
        job.status = IngestStatus.parsing
        rows = load(filename, raw=blob)
        doc_id = new_doc_id(filename)
        chunks = []
        job.status = IngestStatus.chunking
        for row in rows:
            chunks.extend(
                chunk_text(row["text"], doc_id=doc_id, meta={**row.get("meta", {}), **{"tenant": job.tenant}})
            )
        logger.info(f"[{job.job_id}] chunks={len(chunks)}")

        # Embed + write Qdrant
        job.status = IngestStatus.indexing
        embedder = Embedder()
        store = QdrantStore(tenant=job.tenant)
        await store.upsert_chunks(chunks, embedder)

        # KG extract
        job.status = IngestStatus.extracting
        extraction = await extract(chunks)
        kg = Neo4jClient()
        await kg.write_extraction(job.tenant, doc_id, extraction, embedder)
        kg.close()

        # Community refresh (async; per tenant, debounced in prod)
        job.status = IngestStatus.community
        await detect_and_summarize(job.tenant, incremental=True)

        job.status = IngestStatus.done
        job.progress = 1.0
        job.docs_done = 1
    except Exception as e:
        logger.exception(e)
        job.status = IngestStatus.failed
        job.error = str(e)


async def get_job_status(job_id: str) -> IngestJob:
    return _JOBS.get(job_id) or IngestJob(
        job_id=job_id, tenant="unknown", source="?", status=IngestStatus.failed,
        error="not_found",
    )


async def reindex_tenant(tenant: str) -> dict[str, Any]:
    # 占位：读 Neo4j 原始文档/chunk → 重新 embed 到 Qdrant
    # 生产实现：用 Redis Stream 作为 backlog，Ray workers 消费
    return {"tenant": tenant, "status": "scheduled"}
