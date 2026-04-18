FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl poppler-utils tesseract-ocr libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ../pyproject.toml /tmp/pyproject.toml
RUN pip install --upgrade pip && pip install -e /tmp[dev] || pip install fastapi uvicorn pydantic anthropic openai litellm langgraph qdrant-client neo4j redis loguru

COPY . /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
