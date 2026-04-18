"""/query —— 同步 + SSE 流式两条路径。"""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.agents.graph_agent import run_agent_stream
from app.core.security import Principal, PrincipalDep
from app.models.schemas import QueryRequest, QueryResponse, RetrievalMode

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, request: Request, principal: Principal = PrincipalDep):
    router_obj = request.app.state.router
    t0 = time.time()
    if req.mode == RetrievalMode.agentic:
        result = await router_obj.agentic(req, principal)
    else:
        result = await router_obj.run(req, principal)
    result.latency_ms = int((time.time() - t0) * 1000)
    return result


@router.post("/query/stream")
async def query_stream(req: QueryRequest, request: Request, principal: Principal = PrincipalDep):
    async def event_generator():
        async for event in run_agent_stream(req, principal, request.app.state.router):
            if await request.is_disconnected():
                break
            yield {"event": event["type"], "data": event["data"]}
            await asyncio.sleep(0)

    return EventSourceResponse(event_generator())
