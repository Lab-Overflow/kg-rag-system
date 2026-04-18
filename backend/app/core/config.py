"""统一配置入口：pydantic-settings + env + yaml override。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "dev"
    app_secret: str = "change-me"

    # LLM
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    cohere_api_key: str | None = None
    dashscope_api_key: str | None = None
    litellm_base_url: str | None = None
    litellm_master_key: str | None = None

    llm_planner: str = "claude-opus-4-7"
    llm_extractor: str = "claude-haiku-4-5-20251001"
    llm_synthesizer: str = "claude-opus-4-7"
    embedding_model: str = "BAAI/bge-m3"
    sparse_model: str = "naver/splade-v3"
    rerank_model: str = "rerank-v3.5"

    # Infra
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "kgrag_pw"
    qdrant_url: str = "http://qdrant:6333"
    opensearch_url: str = "http://opensearch:9200"
    redis_url: str = "redis://redis:6379/0"
    kafka_bootstrap: str = "kafka:9092"
    ray_address: str | None = None

    # Observability
    otel_exporter_otlp_endpoint: str | None = None
    langfuse_host: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    # App behavior
    max_agent_rounds: int = 3
    default_mode: str = "agentic"
    default_top_k: int = 20
    rerank_top_k: int = 8

    # Paths
    root_dir: Path = Path(__file__).resolve().parents[3]
    config_dir: Path = Field(default_factory=lambda: Path("/app/configs"))


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
