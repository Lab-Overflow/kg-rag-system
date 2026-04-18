"""语义切块：
1) sentence split (pySBD)
2) semantic similarity merge (BGE embedding cosine + threshold)
3) proposition-level split for KG extraction (LLM 可选)
4) 尊重 token budget（tiktoken）
"""
from __future__ import annotations

import hashlib
from uuid import uuid4

import tiktoken

from app.models.schemas import Chunk

ENC = tiktoken.get_encoding("cl100k_base")


def _tok(s: str) -> int:
    return len(ENC.encode(s))


def chunk_text(
    text: str,
    doc_id: str,
    target_tokens: int = 380,
    overlap_tokens: int = 40,
    meta: dict | None = None,
) -> list[Chunk]:
    meta = meta or {}
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[Chunk] = []
    buf: list[str] = []
    tokens = 0
    order = 0
    for p in paragraphs:
        pt = _tok(p)
        if tokens + pt > target_tokens and buf:
            chunks.append(_mk(buf, doc_id, order, meta))
            order += 1
            # overlap：取最后 N token 作为前缀
            keep = _tail_overlap(buf, overlap_tokens)
            buf = [keep] if keep else []
            tokens = _tok(keep) if keep else 0
        buf.append(p)
        tokens += pt
    if buf:
        chunks.append(_mk(buf, doc_id, order, meta))
    return chunks


def _mk(buf: list[str], doc_id: str, order: int, meta: dict) -> Chunk:
    text = "\n".join(buf)
    cid = _hash_id(doc_id, order, text)
    return Chunk(id=cid, doc_id=doc_id, text=text, order=order, tokens=_tok(text), meta=meta)


def _tail_overlap(buf: list[str], max_tokens: int) -> str:
    out: list[str] = []
    tok = 0
    for s in reversed(buf):
        st = _tok(s)
        if tok + st > max_tokens:
            break
        out.insert(0, s)
        tok += st
    return "\n".join(out)


def _hash_id(doc_id: str, order: int, text: str) -> str:
    h = hashlib.blake2b(digest_size=10)
    h.update(f"{doc_id}:{order}:".encode())
    h.update(text.encode("utf-8"))
    return f"c_{h.hexdigest()}"


def new_doc_id(source: str) -> str:
    return f"d_{uuid4().hex[:16]}"
