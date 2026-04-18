"""/graph —— 图谱探索 API（给前端 3D 可视化用）。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.security import Principal, PrincipalDep

router = APIRouter()


class SubgraphQuery(BaseModel):
    seed: str | None = None      # 实体名或 id
    hops: int = 2
    limit: int = 300
    min_confidence: float = 0.0


@router.post("/graph/subgraph")
async def subgraph(q: SubgraphQuery, request: Request, principal: Principal = PrincipalDep):
    kg = request.app.state.kg
    return await kg.subgraph(
        tenant=principal.tenant, seed=q.seed, hops=q.hops,
        limit=q.limit, min_confidence=q.min_confidence,
    )


@router.get("/graph/communities")
async def communities(request: Request, principal: Principal = PrincipalDep):
    kg = request.app.state.kg
    return await kg.list_communities(tenant=principal.tenant)


@router.get("/graph/stats")
async def stats(request: Request, principal: Principal = PrincipalDep):
    return await request.app.state.kg.stats(tenant=principal.tenant)
