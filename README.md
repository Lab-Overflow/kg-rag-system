# KG-RAG · 可扩展知识图谱 RAG 系统

> 面向生产的、下一代 Knowledge Graph RAG Demo。融合 **GraphRAG · LightRAG · HippoRAG 2 · Agentic RAG · ColBERT 晚期交互 · MCP 协议** 等 2025 年代最新范式，以**可扩展性**为第一原则。

```
作者：付宇江 · Agentic Fullstack Engineer
日期：2026-04-18
```

---

## 1 · 核心特性一览

| 维度 | 实现方案 | 关键技术 |
|---|---|---|
| **图谱构建** | LLM-schema-guided 抽取 + 实体消歧 + 多跳补全 | GPT-4o / Claude Opus / Qwen 3，RebeL，LLM-JSON-schema 约束 |
| **图存储** | 属性图 + 向量索引一体化 | Neo4j 5.x (GDS 2.x) / Memgraph / Nebula Graph |
| **向量存储** | 多租户、分片、Hybrid | Qdrant 1.x (Scalar/BQ 量化) + SPLADE 稀疏 |
| **检索** | Hybrid (Dense + Sparse + BM25 + Graph) + Late-Interaction | ColBERTv2 / ColPali（多模态）+ BGE-M3 + Cohere Rerank-v3 |
| **图谱检索** | Personalized PageRank + 社区摘要 + 子图提取 | HippoRAG2 · Microsoft GraphRAG · LightRAG dual-level |
| **Agent 编排** | 计划-执行-反思循环 | LangGraph 0.2 · Plan → Retrieve → Critique → Synthesize |
| **协议互通** | MCP Server/Client 双端 | `mcp` SDK，把 KG 工具暴露给 Claude/Cursor/Dify |
| **评估** | 在线离线一体 | RAGAS · TruLens · Phoenix 追踪 · LangFuse |
| **可扩展** | 水平扩缩、冷热分层、批流一体 | Ray / Kafka / Redis Streams / K8s HPA + KEDA |
| **前端** | 3D 图谱探索 + 对话 + Ingest UI | React 18 · Three.js (react-force-graph) · Tailwind |

---


## 2 · 系统架构总览

```
                         ┌───────────────────────────────────────────┐
                         │                Frontend                   │
                         │  React + Three.js 3D KG + Chat + Admin    │
                         └───────────────▲───────────────────────────┘
                                         │ SSE/WebSocket
┌────────────────────────────────────────┼────────────────────────────────────────┐
│                               FastAPI Gateway (async)                           │
│  /query  /ingest  /graph  /admin  /mcp  /eval                                  │
└───────▲────────────▲──────────────▲──────────────▲────────────▲─────────────────┘
        │            │              │              │            │
   ┌────┴─────┐ ┌────┴────┐   ┌─────┴─────┐  ┌─────┴────┐  ┌────┴────┐
   │ Agent    │ │ Ingest  │   │ Retrieval │  │ KG Ops   │  │ Eval    │
   │ LangGraph│ │ Pipeline│   │ Router    │  │ & Schema │  │ RAGAS   │
   └────┬─────┘ └────┬────┘   └─────┬─────┘  └─────┬────┘  └─────────┘
        │            │ Ray/Prefect  │              │
        ▼            ▼              ▼              ▼
   ┌──────────────────────────────────────────────────────┐
   │              Storage & Infra Layer                   │
   │  Neo4j(+GDS) │ Qdrant │ OpenSearch │ Redis │ Kafka   │
   └──────────────────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │   Observability: OTEL   │
                │  Phoenix + LangFuse +   │
                │  Grafana + Prometheus   │
                └─────────────────────────┘
```

详见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

---

## 3 · 目录结构

```
能够处理知识图谱的RAG System/
├── README.md                # 本文件
├── docs/
│   ├── ARCHITECTURE.md      # 架构深度说明
│   ├── ROADMAP.md           # 演进路线
│   └── EVAL.md              # 评估方法
├── docker-compose.yml       # 一键本地起全栈
├── Makefile
├── pyproject.toml
├── .env.example
├── backend/                 # Python · FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/      # ingest/query/graph/admin/mcp
│   │   ├── core/            # config, logging, security
│   │   ├── ingestion/       # loader, chunker, extractor, pipeline(Ray)
│   │   ├── kg/              # schema, neo4j_client, community, summarizer
│   │   ├── retrieval/       # hybrid, graph_retriever, colbert, reranker, router
│   │   ├── agents/          # LangGraph agent, planner, critic, tools
│   │   ├── mcp/             # MCP server 暴露工具
│   │   ├── eval/            # RAGAS 基准
│   │   ├── observability/   # OTEL, LangFuse
│   │   └── models/          # Pydantic schema
│   └── Dockerfile
├── frontend/                # React + TS + Three.js
│   ├── src/pages/           # Chat · GraphExplorer · Ingest
│   └── Dockerfile
├── infra/
│   ├── k8s/                 # 全套 K8s manifests
│   ├── helm/                # Helm chart
│   └── terraform/           # IaC
├── scripts/                 # seed, migrate, build_kg
├── notebooks/               # 实验 notebook
├── configs/                 # yaml 配置（schema, prompts）
└── data/sample/             # 示例语料
```

---

## 4 · 快速开始

```bash
# 1. 克隆并启动
cp .env.example .env                # 填入 OPENAI / ANTHROPIC / COHERE key
make up                              # docker compose up -d (Neo4j/Qdrant/Redis/Kafka/backend/frontend)

# 2. 灌一份示例语料（维基人物 + 金融研报）
make seed

# 3. 构图（异步任务，可在 /admin 监控）
curl -X POST localhost:8000/api/ingest -F "file=@data/sample/wiki.jsonl"

# 4. 提问
curl -X POST localhost:8000/api/query \
     -H "Content-Type: application/json" \
     -d '{"q":"比较 OpenAI 与 Anthropic 的资本结构", "mode":"agentic"}'

# 5. 打开 http://localhost:5173
#    - /chat           对话式检索（流式）
#    - /graph          3D 图谱探索
#    - /ingest         文档上传 + 实时进度
#    - /eval           RAGAS 面板
```

---

## 5 · 查询模式（动态路由）

路由器根据问题特征选择合适的策略，详见 `backend/app/retrieval/router.py`。

| 模式 | 触发条件 | 检索策略 |
|---|---|---|
| `naive` | 事实/短查询 | Dense top-k → Rerank |
| `hybrid` | 默认 | Dense + SPLADE + BM25 → RRF → Rerank |
| `local_graph` | 命名实体密集 | 实体链接 → 1-2 跳子图 → 上下文拼接 |
| `global_graph` | 概括/跨主题 | 社区摘要层级遍历（GraphRAG Map-Reduce） |
| `agentic` | 多跳/比较/推理 | LangGraph：Plan → 多轮检索 → Critique → 合成 |
| `hippo` | 关联记忆型 | 实体种子 + Personalized PageRank |
| `colpali` | 含图表/PDF | ColPali 多模态 late-interaction |

---

## 6 · 可扩展性设计（Scalability First）

| 维度 | 设计 |
|---|---|
| **写入** | Kafka 分区吞吐 + Ray 并行抽取 + Neo4j batch UNWIND |
| **读取** | Qdrant shard/replica + Neo4j read replica + Redis result cache(TTL) |
| **计算** | 嵌入/重排独立微服务；GPU 节点 HPA，按 QPS+队列深度触发 |
| **冷热分层** | 热：Qdrant 内存量化；温：Qdrant on-disk；冷：S3 + 懒加载 |
| **多租户** | 每租户独立 collection / Neo4j label 前缀 / RLS 策略 |
| **回压** | 令牌桶 + 队列长度反馈到 SSE 客户端 |
| **批流一体** | Ingest 走批（Spark/Ray）；增量走流（Kafka→Worker） |
| **幂等** | 所有抽取任务带 `content_hash + schema_version`，去重写入 |

---

## 7 · 前沿特性要点

- **LightRAG dual-level retrieval**：同时在 "具体实体" 与 "高层主题" 两个粒度检索，合并形成上下文。
- **HippoRAG 2**：把 KG 当作长期记忆，通过 Personalized PageRank 模拟海马体联想。
- **GraphRAG**：Leiden 社区发现 + 多级摘要，支持 "宏观问题"。
- **Agentic Self-Reflection**：Critic 节点判定答案充分度，不足则触发二次检索，最多 N 轮。
- **ColPali**：对含图表的 PDF 直接做视觉 patch 级检索，跳过 OCR。
- **MCP 原生**：后端同时是一个 MCP Server，可被 Claude Desktop / Cursor 直接调用 `kg.query` 工具。
- **Structured Output**：所有 LLM 抽取采用 JSON Schema 强约束（OpenAI Structured Outputs / Anthropic tool use）。

---

## 8 · 评估

| 指标 | 方法 |
|---|---|
| **Faithfulness / Relevance** | RAGAS |
| **多跳推理准确率** | MuSiQue / HotpotQA 子集 |
| **图谱质量** | 关系三元组 Precision/Recall（人工标注 300 条） |
| **时延 P95 / P99** | Phoenix + Prometheus |
| **成本/查询** | Token 账本 + LangFuse |

离线基准脚本：`backend/app/eval/benchmark.py`。

---

## 9 · 路线图

见 [`docs/ROADMAP.md`](docs/ROADMAP.md)。v0.1（本 Demo）→ v0.3（多模态）→ v1.0（Serverless 化）。

---

## 10 · License

Apache License 2.0 · 见 [`LICENSE`](LICENSE)。
