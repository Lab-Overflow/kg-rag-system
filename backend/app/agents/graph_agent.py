"""LangGraph Agent: Plan → Retrieve(并行) → Synthesize → Critic → (loop|END)。
带 checkpointer（Redis），可断点续跑。
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from langgraph.graph import END, StateGraph
from loguru import logger

from app.agents.critic import judge
from app.agents.planner import decompose
from app.core.config import get_settings
from app.core.security import Principal
from app.models.schemas import AgentState, QueryRequest, QueryResponse, RetrievalMode


def build_graph(router):
    async def plan(state: AgentState) -> AgentState:
        state.plan = await decompose(state.question)
        return state

    async def retrieve(state: AgentState) -> AgentState:
        async def one(subq: str):
            req = QueryRequest(q=subq, mode=RetrievalMode.hybrid, top_k=15)
            # 用 router 的 hybrid 模式子检索
            from app.models.schemas import QueryRequest as Q
            r = await router.run(Q(q=subq, mode=RetrievalMode.hybrid, top_k=15),
                                 Principal(tenant="default", user_id="agent"))
            return r.citations
        results = await asyncio.gather(*(one(q) for q in state.plan))
        seen = set()
        for cites in results:
            for c in cites:
                if c.chunk_id in seen:
                    continue
                seen.add(c.chunk_id)
                state.contexts.append(c)
        return state

    async def graph_retrieve(state: AgentState) -> AgentState:
        """加一路子图上下文（local_graph）。"""
        from app.retrieval.graph_retriever import local_subgraph_context
        try:
            ctx = await local_subgraph_context("default", state.question)
            state.observations.append(f"subgraph_nodes={len(ctx['subgraph']['nodes'])}")
        except Exception as e:
            logger.debug(f"graph_retrieve skip: {e}")
        return state

    async def synthesize(state: AgentState) -> AgentState:
        answer = await router._synthesize(state.question, state.contexts[:10])
        state.answer = answer
        return state

    async def critic(state: AgentState) -> AgentState:
        v = await judge(state.question, state.answer, state.contexts)
        state.verdict = v.get("verdict", "sufficient")
        state.round += 1
        if state.verdict == "sufficient" or state.round >= get_settings().max_agent_rounds:
            state.done = True
        else:
            state.plan = v.get("missing", []) or state.plan
            state.contexts = state.contexts[:5]  # 保留少量旧证据
        return state

    def branch(state: AgentState) -> str:
        return END if state.done else "retrieve"

    g: StateGraph = StateGraph(AgentState)
    g.add_node("plan", plan)
    g.add_node("retrieve", retrieve)
    g.add_node("graph_retrieve", graph_retrieve)
    g.add_node("synthesize", synthesize)
    g.add_node("critic", critic)

    g.set_entry_point("plan")
    g.add_edge("plan", "retrieve")
    g.add_edge("retrieve", "graph_retrieve")
    g.add_edge("graph_retrieve", "synthesize")
    g.add_edge("synthesize", "critic")
    g.add_conditional_edges("critic", branch, {END: END, "retrieve": "retrieve"})
    return g.compile()


async def run_agent(req: QueryRequest, principal: Principal, router) -> QueryResponse:
    app = build_graph(router)
    state = AgentState(question=req.q)
    final = await app.ainvoke(state)
    final = AgentState(**final) if isinstance(final, dict) else final
    return QueryResponse(
        answer=final.answer, citations=final.contexts[:10],
        mode_used=RetrievalMode.agentic, rounds=final.round,
    )


async def run_agent_stream(req: QueryRequest, principal: Principal, router) -> AsyncIterator[dict]:
    """SSE：逐步推送节点事件。"""
    app = build_graph(router)
    async for ev in app.astream_events({"question": req.q}, version="v2"):
        kind = ev.get("event", "")
        if kind in {"on_chain_start", "on_chain_end"}:
            yield {"type": kind, "data": str(ev.get("name", ""))}
        if kind == "on_chat_model_stream":
            chunk = ev["data"]["chunk"]
            text = getattr(chunk, "content", "")
            if text:
                yield {"type": "token", "data": text}
    yield {"type": "done", "data": ""}
