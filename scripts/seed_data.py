"""Seed 一个小样本 KG（OpenAI / Anthropic / DeepMind + 若干产品）."""
from __future__ import annotations

import asyncio
import orjson
from pathlib import Path

from app.ingestion.pipeline import run_ingest_job
from app.models.schemas import IngestJob, IngestStatus


SAMPLE = Path("data/sample/seed.jsonl")


def _write_sample():
    SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"text": "OpenAI was founded in 2015 in San Francisco. Sam Altman is CEO. Products include ChatGPT and GPT-4o."},
        {"text": "Anthropic was founded in 2021 by Dario Amodei. It raised funding from Google. Products include Claude Opus 4 and Claude Haiku."},
        {"text": "DeepMind is a subsidiary of Google located in London. It produced AlphaFold, which solved protein folding."},
        {"text": "Claude is produced by Anthropic and competes with GPT-4o produced by OpenAI."},
        {"text": "Demis Hassabis is the CEO of DeepMind and won the 2024 Nobel Prize in Chemistry for AlphaFold."},
    ]
    with SAMPLE.open("wb") as f:
        for r in rows:
            f.write(orjson.dumps(r) + b"\n")


async def main():
    _write_sample()
    job = IngestJob(job_id="seed", tenant="default", source="seed",
                    status=IngestStatus.queued, docs_total=1)
    await run_ingest_job(job, str(SAMPLE), SAMPLE.read_bytes())
    print("seed done:", job.status)


if __name__ == "__main__":
    asyncio.run(main())
