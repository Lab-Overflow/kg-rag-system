"""API & 内部数据结构。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============== Retrieval ==================
class RetrievalMode(str, Enum):
    naive = "naive"
    hybrid = "hybrid"
    local_graph = "local_graph"
    global_graph = "global_graph"
    hippo = "hippo"
    colpali = "colpali"
    agentic = "agentic"


class QueryRequest(BaseModel):
    q: str
    mode: RetrievalMode = RetrievalMode.agentic
    top_k: int = 20
    tenant: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


class Citation(BaseModel):
    chunk_id: str
    doc_id: str
    score: float
    snippet: str
    source: str


class SubgraphPayload(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    subgraph: SubgraphPayload | None = None
    mode_used: RetrievalMode
    rounds: int = 1
    cost_usd: float = 0.0
    latency_ms: int = 0
    trace_id: str | None = None


# =============== Ingestion ==================
class IngestStatus(str, Enum):
    queued = "queued"
    parsing = "parsing"
    chunking = "chunking"
    extracting = "extracting"
    indexing = "indexing"
    community = "community"
    done = "done"
    failed = "failed"


class IngestJob(BaseModel):
    job_id: str
    tenant: str
    source: str
    status: IngestStatus
    progress: float = 0.0
    docs_total: int = 0
    docs_done: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============== KG =========================
class Entity(BaseModel):
    id: str
    name: str
    type: str
    aliases: list[str] = []
    description: str | None = None
    embedding: list[float] | None = None


class Relation(BaseModel):
    head: str
    tail: str
    type: str
    weight: float = 1.0
    evidence: list[str] = Field(default_factory=list)  # chunk ids
    confidence: float = 1.0


class ExtractionResult(BaseModel):
    entities: list[Entity]
    relations: list[Relation]
    claims: list[str] = []


# =============== Chunk ======================
class Chunk(BaseModel):
    id: str
    doc_id: str
    text: str
    order: int
    tokens: int
    meta: dict[str, Any] = Field(default_factory=dict)


# =============== Agent State ================
class AgentState(BaseModel):
    question: str
    plan: list[str] = []
    observations: list[str] = []
    contexts: list[Citation] = []
    answer: str = ""
    round: int = 0
    done: bool = False
    verdict: Literal["sufficient", "insufficient", "unknown"] = "unknown"
