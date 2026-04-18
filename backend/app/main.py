"""FastAPI 入口：装配所有模块 + OTEL + 生命周期。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, graph, ingest, mcp as mcp_api, query
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.observability.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    setup_tracing(app)
    # eager-init heavy singletons (embedders, neo4j driver, qdrant client)
    from app.retrieval.router import RetrievalRouter
    from app.kg.neo4j_client import Neo4jClient
    app.state.router = RetrievalRouter()
    app.state.kg = Neo4jClient()
    yield
    app.state.kg.close()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="KG-RAG",
        description="Scalable Knowledge Graph RAG System",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if s.app_env == "dev" else ["https://your.domain"],
        allow_methods=["*"], allow_headers=["*"],
    )
    app.include_router(query.router, prefix="/api", tags=["query"])
    app.include_router(ingest.router, prefix="/api", tags=["ingest"])
    app.include_router(graph.router, prefix="/api", tags=["graph"])
    app.include_router(admin.router, prefix="/api", tags=["admin"])
    app.include_router(mcp_api.router, prefix="/api", tags=["mcp"])

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": s.app_env}

    return app


app = create_app()
