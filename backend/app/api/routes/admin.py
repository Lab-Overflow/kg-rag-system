"""/admin —— 运维、重建索引、社区发现触发。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.security import Principal, PrincipalDep

router = APIRouter()


@router.post("/admin/rebuild-community")
async def rebuild_community(request: Request, principal: Principal = PrincipalDep):
    from app.kg.community import detect_and_summarize
    return await detect_and_summarize(principal.tenant)


@router.post("/admin/reindex")
async def reindex(request: Request, principal: Principal = PrincipalDep):
    # 触发全量 reindex 到 qdrant/opensearch
    from app.ingestion.pipeline import reindex_tenant
    return await reindex_tenant(principal.tenant)


@router.get("/admin/config")
async def show_config():
    from app.core.config import get_settings
    s = get_settings()
    redacted = s.model_dump()
    for k in list(redacted):
        if "key" in k or "password" in k or "secret" in k:
            redacted[k] = "***"
    return redacted
