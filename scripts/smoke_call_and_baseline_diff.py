"""Smoke test: direct callable dataset + baseline before/after comparison report.

This script does NOT require LLM inference. It focuses on:
1) direct HTTP-callability of dataset files (as website subpage simulation)
2) baseline differences (Simple/Medium/Strong/Boss) using retrieval coverage proxy
3) input/output examples report generation
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
import socket
import threading
import time
from typing import Any
import urllib.request

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


REQUIRED_FILES = [
    "test_public.jsonl",
    "test_private.jsonl",
    "chunks.jsonl",
    "triples.jsonl",
    "entity_alias.json",
    "manifest.json",
]


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def tokenize_zh(text: str) -> list[str]:
    lowered = text.lower()
    zh_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    zh_bigrams = [a + b for a, b in zip(zh_chars, zh_chars[1:])]
    alnum = re.findall(r"[A-Za-z0-9_]+", lowered)
    return zh_chars + zh_bigrams + alnum


def overlap_score(query: str, text: str) -> int:
    q = Counter(tokenize_zh(query))
    t = Counter(tokenize_zh(text))
    common = set(q) & set(t)
    return sum(min(q[k], t[k]) for k in common)


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


@dataclass
class SmokeResult:
    file_name: str
    ok: bool
    detail: str


def start_server(serve_dir: Path, port: int) -> ThreadingHTTPServer:
    handler = QuietHandler
    # py311 SimpleHTTPRequestHandler supports "directory" by partial
    import functools

    factory = functools.partial(handler, directory=str(serve_dir))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), factory)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    return httpd


def direct_call_smoke(base_url: str) -> list[SmokeResult]:
    out: list[SmokeResult] = []
    for name in REQUIRED_FILES:
        url = f"{base_url.rstrip('/')}/{name}"
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                data = resp.read()
                ok = resp.status == 200 and len(data) > 0
                out.append(
                    SmokeResult(
                        file_name=name,
                        ok=ok,
                        detail=f"status={resp.status}, bytes={len(data)}",
                    )
                )
        except Exception as exc:  # pragma: no cover
            out.append(SmokeResult(file_name=name, ok=False, detail=str(exc)))
    return out


def build_alias_lookup(alias_obj: dict[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in alias_obj.items():
        c = str(canonical).strip()
        lookup[c] = c
        if isinstance(aliases, list):
            for a in aliases:
                lookup[str(a).strip()] = c
    return lookup


def find_seed_entities(query: str, alias_lookup: dict[str, str], max_seeds: int = 6) -> list[str]:
    q = query.strip()
    # long-first match to avoid short alias collisions
    items = sorted(alias_lookup.items(), key=lambda x: len(x[0]), reverse=True)
    found: list[str] = []
    seen = set()
    for alias, canonical in items:
        if alias and alias in q and canonical not in seen:
            found.append(canonical)
            seen.add(canonical)
            if len(found) >= max_seeds:
                break
    return found


def medium_retrieve_chunk_ids(query: str, chunks: list[dict], k: int = 8) -> list[str]:
    ranked = sorted(
        chunks,
        key=lambda row: overlap_score(query, row["text"]),
        reverse=True,
    )
    return [row["chunk_id"] for row in ranked[:k]]


def kg_expand(
    query: str,
    triples: list[dict],
    alias_lookup: dict[str, str],
    hops: int,
    max_triples: int,
) -> tuple[set[str], set[str]]:
    # returns (triple_ids, evidence_chunk_ids)
    graph = defaultdict(list)
    for t in triples:
        h, ta = t["head"], t["tail"]
        graph[h].append(t)
        graph[ta].append(t)

    frontier = find_seed_entities(query, alias_lookup)
    visited = set(frontier)
    out_triples: list[dict] = []

    for _ in range(hops):
        nxt = []
        for node in frontier:
            for t in graph.get(node, []):
                out_triples.append(t)
                other = t["tail"] if t["head"] == node else t["head"]
                if other not in visited:
                    visited.add(other)
                    nxt.append(other)
                if len(out_triples) >= max_triples:
                    break
            if len(out_triples) >= max_triples:
                break
        frontier = nxt
        if not frontier or len(out_triples) >= max_triples:
            break

    triple_ids = {t["triple_id"] for t in out_triples}
    ev_chunks = set()
    for t in out_triples:
        for cid in t.get("evidence_chunk_ids", []):
            ev_chunks.add(cid)
    return triple_ids, ev_chunks


def eval_mode(
    queries: list[dict],
    chunks: list[dict],
    triples: list[dict],
    alias_lookup: dict[str, str],
    mode: str,
) -> tuple[float, list[dict]]:
    examples: list[dict] = []
    correct = 0

    for row in queries:
        q = row["query"]
        ans = row["answer"]
        s_chunks = set(row.get("supporting_chunk_ids", []))
        s_triples = set(row.get("supporting_triples", []))

        if mode == "simple":
            pred = "证据不足"
            ok = pred == ans
            ctx_chunks = set()
            ctx_triples = set()
        elif mode == "medium":
            ctx_chunks = set(medium_retrieve_chunk_ids(q, chunks, k=8))
            ctx_triples = {
                t["triple_id"]
                for t in triples
                if any(cid in ctx_chunks for cid in t.get("evidence_chunk_ids", []))
            }
            can_answer = bool(s_chunks) and s_chunks.issubset(ctx_chunks)
            pred = ans if can_answer else "证据不足"
            ok = pred == ans
        elif mode == "strong":
            text_chunks = set(medium_retrieve_chunk_ids(q, chunks, k=10))
            kg_t, kg_c = kg_expand(q, triples, alias_lookup, hops=2, max_triples=24)
            ctx_chunks = text_chunks | kg_c
            ctx_triples = kg_t
            can_answer = (bool(s_chunks) and s_chunks.issubset(ctx_chunks)) or (
                bool(s_triples) and s_triples.issubset(ctx_triples)
            )
            pred = ans if can_answer else "证据不足"
            ok = pred == ans
        elif mode == "boss":
            text_chunks = set(medium_retrieve_chunk_ids(q, chunks, k=15))
            kg_t, kg_c = kg_expand(q, triples, alias_lookup, hops=3, max_triples=36)
            ctx_chunks = text_chunks | kg_c
            ctx_triples = kg_t
            can_answer = (bool(s_chunks) and s_chunks.issubset(ctx_chunks)) or (
                bool(s_triples) and s_triples.issubset(ctx_triples)
            )
            pred = ans if can_answer else "证据不足"
            ok = pred == ans
        else:  # pragma: no cover
            raise ValueError(mode)

        if ok:
            correct += 1
        examples.append(
            {
                "id": row["id"],
                "query": q,
                "gold": ans,
                "pred": pred,
                "ok": ok,
                "support_chunk_hit": list(sorted(s_chunks & ctx_chunks)),
                "support_triple_hit": list(sorted(s_triples & ctx_triples)),
            }
        )

    acc = correct / max(len(queries), 1)
    return acc, examples


def write_report(
    out_path: Path,
    smoke: list[SmokeResult],
    metrics: dict[str, dict[str, float]],
    examples: list[dict],
) -> None:
    lines: list[str] = []
    lines.append("# Baseline Difference & Direct-Call Smoke Report")
    lines.append("")
    lines.append("## 1) Direct call smoke (website subpage simulation)")
    lines.append("")
    lines.append("| File | Status | Detail |")
    lines.append("|---|---|---|")
    for row in smoke:
        lines.append(f"| `{row.file_name}` | {'PASS' if row.ok else 'FAIL'} | {row.detail} |")
    lines.append("")

    lines.append("## 2) Baseline comparison (Simple vs Medium vs Strong vs Boss)")
    lines.append("")
    lines.append("| Split | Simple | Medium | Strong | Boss |")
    lines.append("|---|---:|---:|---:|---:|")
    for split in ("public", "private", "all"):
        m = metrics[split]
        lines.append(
            f"| {split} | {m['simple']:.2%} | {m['medium']:.2%} | {m['strong']:.2%} | {m['boss']:.2%} |"
        )
    lines.append("")

    lines.append("## 3) Input & Output examples (before/after)")
    lines.append("")
    for ex in examples:
        lines.append(f"### {ex['id']}")
        lines.append(f"- Input: `{ex['query']}`")
        lines.append(f"- Gold: `{ex['gold']}`")
        lines.append(f"- Simple output (no RAG): `{ex['simple_pred']}`")
        lines.append(f"- Medium output (text RAG): `{ex['medium_pred']}`")
        lines.append(f"- Strong output (text + KG): `{ex['strong_pred']}`")
        lines.append(f"- Boss output (extended text + KG): `{ex['boss_pred']}`")
        lines.append(
            f"- Delta: simple→strong = `{ex['simple_ok']}`→`{ex['strong_ok']}`, "
            f"simple→boss = `{ex['simple_ok']}`→`{ex['boss_ok']}`"
        )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run direct-call smoke and baseline diff demo.")
    parser.add_argument(
        "--dataset-dir",
        default="data/rag_kg_hongloumeng_v1",
        help="Dataset directory.",
    )
    parser.add_argument(
        "--report",
        default="data/rag_kg_hongloumeng_v1/baseline_demo_report.md",
        help="Output markdown report path.",
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir).resolve()
    if not dataset_dir.exists():
        raise FileNotFoundError(dataset_dir)

    port = pick_free_port()
    httpd = start_server(dataset_dir, port)
    base_url = f"http://127.0.0.1:{port}"

    try:
        smoke = direct_call_smoke(base_url)
        if not all(r.ok for r in smoke):
            bad = [r for r in smoke if not r.ok]
            raise RuntimeError(f"direct call smoke failed: {[b.file_name for b in bad]}")

        chunks = load_jsonl(dataset_dir / "chunks.jsonl")
        triples = load_jsonl(dataset_dir / "triples.jsonl")
        public_q = load_jsonl(dataset_dir / "test_public.jsonl")
        private_q = load_jsonl(dataset_dir / "test_private.jsonl")
        all_q = public_q + private_q
        alias_obj = json.loads((dataset_dir / "entity_alias.json").read_text(encoding="utf-8"))
        alias_lookup = build_alias_lookup(alias_obj)

        metrics: dict[str, dict[str, float]] = {}
        split_rows = {"public": public_q, "private": private_q, "all": all_q}
        for split, rows in split_rows.items():
            s_acc, s_ex = eval_mode(rows, chunks, triples, alias_lookup, "simple")
            m_acc, m_ex = eval_mode(rows, chunks, triples, alias_lookup, "medium")
            st_acc, st_ex = eval_mode(rows, chunks, triples, alias_lookup, "strong")
            b_acc, b_ex = eval_mode(rows, chunks, triples, alias_lookup, "boss")
            metrics[split] = {
                "simple": s_acc,
                "medium": m_acc,
                "strong": st_acc,
                "boss": b_acc,
            }
            # keep per-query aggregates only for ALL split
            if split == "all":
                merged = []
                idx = {x["id"]: x for x in s_ex}
                for arr, key_pred, key_ok in [
                    (s_ex, "simple_pred", "simple_ok"),
                    (m_ex, "medium_pred", "medium_ok"),
                    (st_ex, "strong_pred", "strong_ok"),
                    (b_ex, "boss_pred", "boss_ok"),
                ]:
                    for item in arr:
                        row = idx.setdefault(item["id"], {"id": item["id"], "query": item["query"], "gold": item["gold"]})
                        row[key_pred] = item["pred"]
                        row[key_ok] = item["ok"]
                # fixed examples: first 3 public + first 3 private
                want_ids = [q["id"] for q in public_q[:3]] + [q["id"] for q in private_q[:3]]
                for wid in want_ids:
                    if wid in idx:
                        merged.append(idx[wid])
                example_rows = merged

        report_path = Path(args.report)
        write_report(report_path, smoke, metrics, example_rows)

        summary = {
            "base_url": base_url,
            "smoke_all_pass": all(r.ok for r in smoke),
            "metrics": metrics,
            "report": str(report_path),
        }
        (dataset_dir / "baseline_demo_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
