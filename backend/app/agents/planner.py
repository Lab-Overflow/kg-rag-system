"""Planner + map-reduce helpers used by Router & Agent."""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic
from loguru import logger

from app.core.config import get_settings


async def decompose(query: str, max_sub: int = 4) -> list[str]:
    """Break a complex question into sub-questions.

    Returns list[str]; may be length 1 for simple queries.
    """
    s = get_settings()
    client = AsyncAnthropic(api_key=s.anthropic_api_key)
    prompt = (
        "You are a query planner. Decompose the user's question into the minimum "
        "sub-questions needed to answer it (1–%d). "
        "Return ONLY a JSON list of strings.\n\nQuestion: %s"
        % (max_sub, query)
    )
    try:
        msg = await client.messages.create(
            model=s.llm_planner, max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
        # 尝试强解析 JSON
        start, end = text.find("["), text.rfind("]")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    except Exception as e:
        logger.warning(f"decompose failed: {e}")
    return [query]


async def map_reduce_over_communities(query: str, communities: list[dict]) -> str:
    """GraphRAG global-mode: 对每个社区摘要做局部回答，再合成。"""
    s = get_settings()
    client = AsyncAnthropic(api_key=s.anthropic_api_key)
    partials: list[str] = []
    for c in communities:
        p = (
            "Given this community summary, extract any claims relevant to the user's question. "
            "Return <= 3 bullets or 'N/A'.\n"
            f"Question: {query}\nSummary: {c.get('summary','')}"
        )
        try:
            m = await client.messages.create(
                model=s.llm_extractor, max_tokens=300,
                messages=[{"role": "user", "content": p}],
            )
            partials.append("".join(b.text for b in m.content if hasattr(b, "text")))
        except Exception:
            continue
    reduce_prompt = (
        "Synthesize a concise answer from these partials. "
        "If they conflict, note the conflict. Cite partial index [P1][P2] where helpful.\n\n"
        f"Question: {query}\n\n"
        + "\n\n".join(f"[P{i+1}] {p}" for i, p in enumerate(partials))
    )
    m = await client.messages.create(
        model=s.llm_synthesizer, max_tokens=1024,
        messages=[{"role": "user", "content": reduce_prompt}],
    )
    return "".join(b.text for b in m.content if hasattr(b, "text"))
