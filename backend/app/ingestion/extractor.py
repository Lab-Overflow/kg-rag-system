"""LLM 驱动的实体/关系/声明抽取：
- JSON-schema 强约束（Anthropic tool use / OpenAI Structured Outputs）
- schema-guided：可在 configs/kg_schema.yaml 中配置领域本体
- 两阶段：先抽实体，再以实体列表为上下文抽关系，降低幻觉
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from loguru import logger

from app.core.config import get_settings
from app.models.schemas import Entity, ExtractionResult, Relation


_SYSTEM = """You are a world-class knowledge graph extractor. Follow the ontology strictly.
Return ONLY JSON conforming to the given schema.
Every relation MUST cite the chunk id(s) from which it is evidenced.
Never invent facts not present in the text."""


def load_schema(name: str = "default") -> dict:
    p = Path("/app/configs") / f"kg_schema_{name}.yaml"
    if not p.exists():
        # 兜底 schema
        return {
            "entity_types": ["Person", "Organization", "Product", "Location",
                             "Event", "Concept", "Metric", "Date"],
            "relation_types": ["works_at", "founded", "located_in", "part_of",
                               "produced_by", "competes_with", "subsidiary_of",
                               "happened_at", "influences", "related_to"],
        }
    return yaml.safe_load(p.read_text())


async def extract(chunks: list, schema_name: str = "default") -> ExtractionResult:
    """输入 list[Chunk]，输出合并去重后的抽取结果。"""
    schema = load_schema(schema_name)
    all_ents: dict[str, Entity] = {}
    all_rels: list[Relation] = []
    claims: list[str] = []
    for batch in _batched(chunks, 6):
        res = await _extract_batch(batch, schema)
        for e in res.entities:
            if e.id not in all_ents:
                all_ents[e.id] = e
            else:
                all_ents[e.id].aliases = list(set(all_ents[e.id].aliases + e.aliases))
        all_rels.extend(res.relations)
        claims.extend(res.claims)
    return ExtractionResult(entities=list(all_ents.values()), relations=all_rels, claims=claims)


def _batched(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


async def _extract_batch(chunks: list, schema: dict) -> ExtractionResult:
    from anthropic import AsyncAnthropic
    s = get_settings()
    client = AsyncAnthropic(api_key=s.anthropic_api_key)

    tool = {
        "name": "submit_extraction",
        "description": "Submit entities and relations extracted from the text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string", "enum": schema["entity_types"]},
                            "aliases": {"type": "array", "items": {"type": "string"}},
                            "description": {"type": "string"},
                        },
                        "required": ["name", "type"],
                    },
                },
                "relations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "head": {"type": "string"},
                            "tail": {"type": "string"},
                            "type": {"type": "string", "enum": schema["relation_types"]},
                            "evidence_chunk_ids": {
                                "type": "array", "items": {"type": "string"},
                            },
                            "confidence": {"type": "number"},
                        },
                        "required": ["head", "tail", "type"],
                    },
                },
                "claims": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["entities", "relations"],
        },
    }
    rendered = "\n\n".join(f"[chunk {c.id}]\n{c.text}" for c in chunks)
    try:
        msg = await client.messages.create(
            model=s.llm_extractor,
            max_tokens=4096,
            system=_SYSTEM,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_extraction"},
            messages=[{"role": "user", "content": rendered}],
        )
        payload = next(
            (b.input for b in msg.content if getattr(b, "type", None) == "tool_use"),
            {"entities": [], "relations": []},
        )
    except Exception as e:
        logger.exception(f"extraction failed: {e}")
        payload = {"entities": [], "relations": []}

    ents = [Entity(id=_ent_id(e["name"], e["type"]), **e) for e in payload.get("entities", [])]
    rels = [
        Relation(
            head=_ent_id(r["head"], _guess_type(r["head"], ents)),
            tail=_ent_id(r["tail"], _guess_type(r["tail"], ents)),
            type=r["type"],
            evidence=r.get("evidence_chunk_ids", []),
            confidence=float(r.get("confidence", 0.8)),
        )
        for r in payload.get("relations", [])
    ]
    return ExtractionResult(entities=ents, relations=rels, claims=payload.get("claims", []))


def _ent_id(name: str, etype: str) -> str:
    import hashlib
    slug = hashlib.blake2b(f"{etype}:{name.lower().strip()}".encode(), digest_size=8).hexdigest()
    return f"e_{slug}"


def _guess_type(name: str, ents: list[Entity]) -> str:
    for e in ents:
        if e.name == name:
            return e.type
    return "Concept"
