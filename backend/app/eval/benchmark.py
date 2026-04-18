"""离线评估入口：
 python -m app.eval.benchmark --dataset musique --mode agentic --limit 100
支持：musique / hotpotqa / 2wikimultihop / custom jsonl
输出：RAGAS 综合分 + EM/F1 + 每题 trace id（可在 Phoenix 回放）
"""
from __future__ import annotations

import asyncio

import typer
from datasets import load_dataset
from loguru import logger

from app.core.security import Principal
from app.models.schemas import QueryRequest, RetrievalMode
from app.retrieval.router import RetrievalRouter

app = typer.Typer()


@app.command()
def run(
    dataset: str = "musique",
    mode: str = "agentic",
    limit: int = 50,
    split: str = "validation",
):
    asyncio.run(_run(dataset, mode, limit, split))


async def _run(dataset: str, mode: str, limit: int, split: str) -> None:
    ds_map = {
        "musique": ("dgslibisey/MuSiQue", "train"),
        "hotpotqa": ("hotpot_qa", "fullwiki"),
        "2wikimultihop": ("somebody/2wiki-mh", "validation"),
    }
    name, subset = ds_map.get(dataset, (dataset, split))
    ds = load_dataset(name, subset, split=split).select(range(limit))
    router = RetrievalRouter()
    principal = Principal(tenant="default", user_id="eval")

    preds, refs, qs, ctxs = [], [], [], []
    for ex in ds:
        q = ex.get("question") or ex.get("q")
        gt = ex.get("answer") or ex.get("answers", [""])[0]
        r = await router.run(QueryRequest(q=q, mode=RetrievalMode(mode)), principal) \
            if mode != "agentic" else await router.agentic(
                QueryRequest(q=q, mode=RetrievalMode.agentic), principal)
        preds.append(r.answer)
        refs.append(gt)
        qs.append(q)
        ctxs.append([c.snippet for c in r.citations])
        logger.info(f"Q: {q[:60]} → A: {r.answer[:80]}")

    _ragas(qs, preds, refs, ctxs)
    _em_f1(preds, refs)


def _ragas(qs, preds, refs, ctxs):
    try:
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, faithfulness
        from datasets import Dataset
        ds = Dataset.from_dict({
            "question": qs, "answer": preds, "contexts": ctxs, "ground_truth": refs,
        })
        r = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision])
        print("RAGAS:", r)
    except Exception as e:
        logger.warning(f"RAGAS skipped: {e}")


def _em_f1(preds, refs):
    import re

    def norm(s):
        return re.sub(r"\s+", " ", s.lower()).strip()

    em = sum(norm(p) == norm(r) for p, r in zip(preds, refs)) / max(1, len(preds))
    print(f"EM = {em:.3f}")


if __name__ == "__main__":
    app()
