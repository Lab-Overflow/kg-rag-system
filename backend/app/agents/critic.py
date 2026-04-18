"""Critic node：judge if current evidence is sufficient. 返回 verdict + 缺口。"""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic
from loguru import logger

from app.core.config import get_settings
from app.models.schemas import Citation


async def judge(question: str, draft: str, cites: list[Citation]) -> dict:
    s = get_settings()
    client = AsyncAnthropic(api_key=s.anthropic_api_key)
    ctx = "\n".join(f"[{i+1}] {c.snippet}" for i, c in enumerate(cites[:8]))
    prompt = (
        "You judge answer quality. Return JSON "
        '{"verdict":"sufficient|insufficient","missing":["..."],"reason":"..."}.\n\n'
        f"Question: {question}\nDraft:\n{draft}\nEvidence:\n{ctx}"
    )
    try:
        msg = await client.messages.create(
            model=s.llm_extractor, max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    except Exception as e:
        logger.warning(f"critic failed: {e}")
    return {"verdict": "sufficient", "missing": [], "reason": "fallback"}
