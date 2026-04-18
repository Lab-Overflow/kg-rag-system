"""Kafka consumer — 生产 ingestion worker。KEDA 按 lag 扩缩。"""
from __future__ import annotations

import asyncio
import orjson
from aiokafka import AIOKafkaConsumer
from loguru import logger

from app.core.config import get_settings
from app.ingestion.pipeline import run_ingest_job
from app.models.schemas import IngestJob, IngestStatus


TOPIC = "kgrag.ingest"


async def run():
    s = get_settings()
    consumer = AIOKafkaConsumer(
        TOPIC, bootstrap_servers=s.kafka_bootstrap,
        group_id="ingest-worker", auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            payload = orjson.loads(msg.value)
            job = IngestJob(
                job_id=payload["job_id"], tenant=payload["tenant"],
                source=payload.get("source", "kafka"),
                status=IngestStatus.queued, docs_total=1,
            )
            logger.info(f"consume {job.job_id}")
            await run_ingest_job(job, payload["filename"],
                                 bytes.fromhex(payload["blob_hex"]))
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run())
