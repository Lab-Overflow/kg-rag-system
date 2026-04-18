"""OTEL 接入 Arize Phoenix + 自动 instrument FastAPI & LLM 调用。"""
from __future__ import annotations

from fastapi import FastAPI
from loguru import logger

from app.core.config import get_settings


def setup_tracing(app: FastAPI) -> None:
    s = get_settings()
    if not s.otel_exporter_otlp_endpoint:
        logger.info("OTEL not configured, skipping")
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "kg-rag", "env": s.app_env})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{s.otel_exporter_otlp_endpoint}/v1/traces")
        ))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OTEL tracing enabled")
    except Exception as e:  # pragma: no cover
        logger.warning(f"OTEL setup failed: {e}")
