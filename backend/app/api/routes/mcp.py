"""HTTP façade over the MCP tools — 方便 Web 直接试用。
真正的 MCP stdio server 在 app/mcp/server.py。
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class ToolCall(BaseModel):
    name: str
    arguments: dict


@router.get("/mcp/tools")
async def list_tools():
    from app.mcp.server import TOOLS
    return [{"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in TOOLS]


@router.post("/mcp/call")
async def call_tool(call: ToolCall, request: Request):
    from app.mcp.server import dispatch
    return await dispatch(call.name, call.arguments, request.app.state)
