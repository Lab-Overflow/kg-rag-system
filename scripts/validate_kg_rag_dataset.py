"""Validate KG-RAG dataset assets with schema and retrieval smoke checks."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fp:
        for ln, line in enumerate(fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{ln} invalid json: {exc}") from exc
    return rows


def tokenize_zh(text: str) -> list[str]:
    # Lightweight tokenizer for smoke test without external deps.
    # Mixes:
    # 1) Chinese single-char tokens (better recall for short Q/A names)
    # 2) Alnum tokens
    # 3) Chinese 2-char shingles for slightly better precision
    lowered = text.lower()
    zh_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    alnum = re.findall(r"[A-Za-z0-9_]+", lowered)
    zh_bigrams = [a + b for a, b in zip(zh_chars, zh_chars[1:])]
    return zh_chars + zh_bigrams + alnum


def overlap_score(query: str, text: str) -> int:
    q = Counter(tokenize_zh(query))
    t = Counter(tokenize_zh(text))
    common = set(q) & set(t)
    return sum(min(q[k], t[k]) for k in common)


def top_k_chunks(query: str, chunks: list[dict], k: int = 8) -> list[str]:
    ranked = sorted(
        ((row["chunk_id"], overlap_score(query, row["text"])) for row in chunks),
        key=lambda x: x[1],
        reverse=True,
    )
    return [cid for cid, _ in ranked[:k]]


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate(base_dir: Path) -> None:
    required = [
        "chunks.jsonl",
        "triples.jsonl",
        "entity_alias.json",
        "test_public.jsonl",
        "test_private.jsonl",
        "manifest.json",
    ]
    for name in required:
        ensure((base_dir / name).exists(), f"missing required file: {name}")

    chunks = load_jsonl(base_dir / "chunks.jsonl")
    triples = load_jsonl(base_dir / "triples.jsonl")
    public_q = load_jsonl(base_dir / "test_public.jsonl")
    private_q = load_jsonl(base_dir / "test_private.jsonl")
    aliases = json.loads((base_dir / "entity_alias.json").read_text(encoding="utf-8"))

    ensure(len(chunks) >= 30, "chunks too small")
    ensure(len(triples) >= 30, "triples too small")
    ensure(len(public_q) >= 20, "public queries too small")
    ensure(len(private_q) >= 10, "private queries too small")
    ensure(isinstance(aliases, dict), "entity_alias.json must be dict")

    chunk_ids = [c.get("chunk_id") for c in chunks]
    ensure(all(chunk_ids), "chunk_id missing in chunks")
    ensure(len(set(chunk_ids)) == len(chunk_ids), "duplicate chunk_id")
    chunk_id_set = set(chunk_ids)

    triple_ids = [t.get("triple_id") for t in triples]
    ensure(all(triple_ids), "triple_id missing in triples")
    ensure(len(set(triple_ids)) == len(triple_ids), "duplicate triple_id")
    triple_id_set = set(triple_ids)

    # entity coverage
    canonical_entities = set(aliases.keys())
    for t in triples:
        for key in ("head", "relation", "tail"):
            ensure(t.get(key), f"triple missing {key}: {t}")
        ev = t.get("evidence_chunk_ids")
        ensure(isinstance(ev, list), f"triple evidence_chunk_ids must be list: {t}")
        for cid in ev:
            ensure(cid in chunk_id_set, f"triple evidence chunk missing: {cid}")
        canonical_entities.add(t["head"])
        canonical_entities.add(t["tail"])

    def check_queries(rows: list[dict], split: str) -> None:
        for q in rows:
            ensure(q.get("id"), f"{split} query missing id: {q}")
            ensure(q.get("query"), f"{split} query missing query: {q}")
            ensure(q.get("answer"), f"{split} query missing answer: {q}")
            supports = q.get("supporting_facts", [])
            ensure(isinstance(supports, list), f"{split} supporting_facts must be list: {q}")
            s_triples = q.get("supporting_triples", [])
            ensure(isinstance(s_triples, list), f"{split} supporting_triples must be list: {q}")
            for tid in s_triples:
                ensure(tid in triple_id_set, f"{split} references missing triple id: {tid}")
            s_chunks = q.get("supporting_chunk_ids", [])
            ensure(isinstance(s_chunks, list), f"{split} supporting_chunk_ids must be list: {q}")
            for cid in s_chunks:
                ensure(cid in chunk_id_set, f"{split} references missing chunk id: {cid}")

    check_queries(public_q, "public")
    check_queries(private_q, "private")

    # Retrieval smoke: answer hit in top-k or support chunk hit in top-k
    def smoke(rows: list[dict], split: str, k: int, threshold: float) -> None:
        ok = 0
        for q in rows:
            topk = top_k_chunks(q["query"], chunks, k=k)
            topk_text = " ".join(c["text"] for c in chunks if c["chunk_id"] in set(topk))
            answer_hit = str(q["answer"]) in topk_text
            support_hit = any(cid in topk for cid in q.get("supporting_chunk_ids", []))
            if answer_hit or support_hit:
                ok += 1
        ratio = ok / max(len(rows), 1)
        ensure(
            ratio >= threshold,
            f"{split} smoke retrieval ratio too low: {ratio:.2%} < {threshold:.2%}",
        )
        print(f"[SMOKE] {split}: {ok}/{len(rows)} ({ratio:.2%})")

    smoke(public_q, "public", k=8, threshold=0.75)
    smoke(private_q, "private", k=10, threshold=0.60)

    print("[OK] Dataset validation passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate KG-RAG dataset artifacts.")
    parser.add_argument(
        "--base-dir",
        default="data/rag_kg_hongloumeng_v1",
        help="Dataset directory to validate.",
    )
    args = parser.parse_args()
    validate(Path(args.base_dir))


if __name__ == "__main__":
    main()
