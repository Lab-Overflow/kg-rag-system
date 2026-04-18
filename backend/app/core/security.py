"""简化的租户 + JWT 校验占位。生产接 OIDC。"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel


class Principal(BaseModel):
    tenant: str
    user_id: str
    roles: list[str] = []


async def get_principal(
    x_tenant: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> Principal:
    # Demo：允许未登录 dev；生产需 verify JWT/OIDC
    if not x_tenant:
        return Principal(tenant="default", user_id="anonymous", roles=["user"])
    if authorization and not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad auth header")
    return Principal(tenant=x_tenant, user_id="dev", roles=["user"])


PrincipalDep = Depends(get_principal)
