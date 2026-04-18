"""多源加载：PDF/DOCX/HTML/Markdown/CSV/JSONL。

优先 Docling（更强版面、表格、公式），回退 Unstructured。
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger


def load(path: str | Path, raw: bytes | None = None) -> list[dict]:
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext in {".pdf", ".docx", ".pptx", ".html", ".md"}:
            return _docling_load(path, raw)
        if ext in {".jsonl"}:
            return _jsonl_load(path, raw)
        if ext in {".txt"}:
            return [{"text": (raw or path.read_bytes()).decode("utf-8", errors="ignore"),
                     "meta": {"source": str(path)}}]
    except Exception as e:  # pragma: no cover
        logger.warning(f"docling failed for {path}: {e}, falling back to unstructured")
    return _unstructured_load(path, raw)


def _docling_load(path: Path, raw: bytes | None) -> list[dict]:
    from docling.document_converter import DocumentConverter
    conv = DocumentConverter()
    src = str(path) if raw is None else _write_tmp(path, raw)
    doc = conv.convert(src).document
    out: list[dict] = []
    for item in doc.iterate_items():
        text = getattr(item, "text", None)
        if not text:
            continue
        out.append({"text": text, "meta": {"source": str(path), "label": item.label.name}})
    return out


def _jsonl_load(path: Path, raw: bytes | None) -> list[dict]:
    import orjson
    lines = (raw or path.read_bytes()).splitlines()
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        obj = orjson.loads(line)
        text = obj.get("text") or obj.get("content") or ""
        meta = {k: v for k, v in obj.items() if k not in ("text", "content")}
        meta["source"] = str(path)
        meta["row"] = i
        out.append({"text": text, "meta": meta})
    return out


def _unstructured_load(path: Path, raw: bytes | None) -> list[dict]:
    from unstructured.partition.auto import partition
    els = partition(filename=str(path)) if raw is None else partition(file=raw)  # type: ignore
    return [{"text": str(e), "meta": {"source": str(path), "category": e.category}}
            for e in els if str(e).strip()]


def _write_tmp(path: Path, raw: bytes) -> str:
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=path.suffix, delete=False)
    tmp.write(raw)
    tmp.flush()
    return tmp.name
