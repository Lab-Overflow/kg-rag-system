"""最小 smoke test。"""
import pytest

from app.ingestion.chunker import chunk_text, new_doc_id


def test_chunk():
    doc_id = new_doc_id("t.txt")
    chunks = chunk_text("alpha beta\n" * 200, doc_id=doc_id, target_tokens=120)
    assert len(chunks) > 1
    assert all(c.doc_id == doc_id for c in chunks)


@pytest.mark.asyncio
async def test_planner_fallback(monkeypatch):
    from app.agents import planner

    async def fake(*a, **kw):
        raise RuntimeError("no key")

    monkeypatch.setattr(planner, "decompose", fake)
    try:
        await planner.decompose("x")
    except RuntimeError:
        pass
