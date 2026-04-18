"""MCP Server — expose KG tools so Claude Desktop / Cursor / Dify can call them natively.

Run: python -m app.mcp.server   (stdio)
Or:  attach to FastAPI HTTP façade at /api/mcp/*.
"""
from __future__ import annotations

import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.agents import tools as T


TOOLS = [
    T.ToolSpec(
        name="kg_query",
        description="Ask the Knowledge-Graph RAG system. Returns answer+citations.",
        input_schema={
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "mode": {
                    "type": "string",
                    "enum": ["naive", "hybrid", "local_graph", "global_graph",
                             "hippo", "agentic"],
                    "default": "agentic",
                },
                "top_k": {"type": "integer", "default": 8},
            },
            "required": ["q"],
        },
    ),
    T.ToolSpec(
        name="kg_subgraph",
        description="Fetch a 1–2 hop subgraph around a seed entity.",
        input_schema={
            "type": "object",
            "properties": {
                "seed": {"type": "string"},
                "hops": {"type": "integer", "default": 2},
                "limit": {"type": "integer", "default": 200},
            },
            "required": ["seed"],
        },
    ),
    T.ToolSpec(
        name="kg_entity_search",
        description="Vector + alias search over entities.",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}, "k": {"type": "integer", "default": 10}},
            "required": ["name"],
        },
    ),
]


async def dispatch(name: str, args: dict, state=None) -> dict:
    if name == "kg_query":
        return await T.kg_query(**args)
    if name == "kg_subgraph":
        return await T.kg_subgraph(**args)
    if name == "kg_entity_search":
        return {"entities": await T.kg_entity_search(**args)}
    raise ValueError(f"unknown tool {name}")


def _mcp_tool(t: T.ToolSpec) -> Tool:
    return Tool(name=t.name, description=t.description, inputSchema=t.input_schema)


async def main() -> None:
    server: Server = Server("kg-rag-mcp")

    @server.list_tools()
    async def _list():
        return [_mcp_tool(t) for t in TOOLS]

    @server.call_tool()
    async def _call(name: str, arguments: dict):
        result = await dispatch(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
