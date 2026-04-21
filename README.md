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
   │  Neo4j(+GDS) │ Qdrant(Vector Database) │ OpenSearch │ Redis │ Kafka   │
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

## 5.1 · 向量数据库（Qdrant）的价值与应用场景

Qdrant 在本系统中承担 `Vector Database` 角色，负责存储与检索 chunk 的 dense/sparse 向量，并与图检索结果融合。

### 核心优势

- **语义召回能力强**：支持基于 embedding 的相似检索，能覆盖关键词不完全重合但语义相关的问题。
- **混合检索友好**：支持 dense + sparse（SPLADE）联合检索，适合中文问答里的“语义 + 关键词”混合场景。
- **工程可扩展**：支持分片、副本与量化，便于在数据规模增大后保持吞吐和成本平衡。
- **多租户过滤清晰**：可基于 payload（如 tenant/doc_id）做精确过滤，便于 SaaS 化隔离。

### 本项目中的典型场景

- **`hybrid` 模式主召回**：先做 dense+sparse 召回，再经 rerank 得到高质量证据块。
- **`local_graph` 模式补充文本证据**：图谱拿到子图后，仍通过向量检索补齐自然语言上下文。
- **`hippo` 模式证据回填**：图算法选出高相关实体后，再回到向量/文档索引拿可引用 chunk。

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

---

## 11 · 附录（协作者阅读）: 设计说明与可行性判断

本节是额外说明，用于帮助协作者快速判断这个 Demo 的设计逻辑、边界与可落地性。

### 11.1 这个项目和普通文本 RAG 的核心差异

| 维度 | 纯文本 RAG | 本项目（KG-RAG） |
|---|---|---|
| 索引单元 | 仅 chunk | chunk + entity + relation + community |
| 检索路径 | 通常 1 条（向量/关键词） | 多路并行（hybrid + graph + hippo + agentic） |
| 推理方式 | 基于相似片段拼接 | 支持路径级多跳推理与社区级摘要推理 |
| 可解释性 | 主要靠 chunk 引用 | chunk 引用 + 图关系路径 |
| 评估维度 | 答案质量 | 答案质量 + 图谱质量 + 多跳准确率 |

### 11.2 为什么说这个方案“可行”

| 可行性来源 | 当前状态 | 说明 |
|---|---|---|
| 端到端链路 | 已具备 | 已有 ingest -> 抽取 -> 入库 -> 检索 -> 回答 的完整流程 |
| 多模式检索 | 已具备 | `hybrid / local_graph / global_graph / hippo / agentic` 可路由 |
| 工程化骨架 | 已具备 | 包含 FastAPI、前端、Docker Compose、K8s/Helm/Terraform 目录 |
| 可扩展接口 | 已具备 | 预留 MCP、Kafka、Ray、评估与观测链路 |
| 演示可读性 | 已具备 | README、ARCHITECTURE、ROADMAP、EVAL 文档齐全 |

### 11.3 当前成熟度边界（协作时务必注意）

| 模块 | 成熟度 | 备注 |
|---|---|---|
| 核心流程（Demo） | 可运行骨架 | 适合概念验证、方案讲解、二次开发起点 |
| `colpali` 模式 | 占位 | 当前返回 placeholder，未完成多模态检索闭环 |
| `reindex_tenant` | 占位 | 已留接口，尚未实现生产级回填流程 |
| 鉴权 | Demo 级 | 当前是简化租户/JWT 占位，生产需接 OIDC/RBAC |
| 测试与 CI | 待补强 | 测试可编译但默认路径配置未完全打通 |

### 11.4 协作者推荐协作方式

1. 第一阶段先把它当“可扩展骨架”，重点验证检索质量与多跳效果，不先追求全功能上线。
2. 第二阶段优先补齐占位项（`colpali`、`reindex`、auth），再推进性能与成本优化。
3. 第三阶段按业务域补 ontology 与评估集，形成可复现实验基线（simple/medium/strong/boss）。

### 11.5 结论

这个方案在 2026-04-18 的状态下，结论是“方向正确、骨架可用、功能分层明确”，适合作为协作研发底座。  
如果目标是生产落地，需要在安全、测试、占位模块与观测闭环上继续工程化推进。

---

## 12 · KG Demo 数据集（可直接调用）

本项目已内置一套可直接用于课程 notebook 调用的 KG-RAG 数据集与自动验证脚本，路径为 `data/rag_kg_hongloumeng_v1/`。

### 12.1 数据集产物

| 文件 | 用途 |
|---|---|
| `test_public.jsonl` | 公开测试集（单跳为主） |
| `test_private.jsonl` | 私有测试集（多跳/比较/聚合） |
| `chunks.jsonl` | 文本检索 chunk 资产 |
| `triples.jsonl` | 知识图谱三元组（含证据 chunk id） |
| `entity_alias.json` | 实体别名映射 |
| `manifest.json` | 数据集元信息与计数 |
| `hongloumeng_fulltext.txt` | 纯文本流程回退文件 |
| `rag_kg_hongloumeng_v1.zip` | 便于上传网站子目录的打包文件 |

### 12.2 从 0 到 1 生成数据集

```bash
python scripts/build_kg_rag_dataset.py --out-dir data/rag_kg_hongloumeng_v1
```

### 12.3 自动校验与 Smoke Test

```bash
# 1) 结构/一致性/检索烟测
python scripts/validate_kg_rag_dataset.py --base-dir data/rag_kg_hongloumeng_v1

# 2) 直接调用 + baseline 前后差异报告
python scripts/smoke_call_and_baseline_diff.py \
  --dataset-dir data/rag_kg_hongloumeng_v1 \
  --report data/rag_kg_hongloumeng_v1/baseline_demo_report.md
```

### 12.4 如何体现 RAG 使用前后差异

自动脚本会生成两个文件：

1. `data/rag_kg_hongloumeng_v1/baseline_demo_summary.json`  
2. `data/rag_kg_hongloumeng_v1/baseline_demo_report.md`

其中报告包含课程风格的两部分：

1. `Simple / Medium / Strong / Boss` 基线对比表。  
2. `Input & Output examples`，展示 no-RAG 与 text-RAG / KG-RAG 的输出差异。

### 12.5 网站子目录部署建议

将 `rag_kg_hongloumeng_v1.zip` 解压上传到你的网站子目录后，确保以下 URL 可访问：

1. `<base_url>/test_public.jsonl`  
2. `<base_url>/test_private.jsonl`  
3. `<base_url>/chunks.jsonl`  
4. `<base_url>/triples.jsonl`  
5. `<base_url>/entity_alias.json`

---

## 13 · 检索策略与召回率（术语归纳）

本节用于协作者快速统一 baseline、retrieval strategy 与评估口径。

### 13.1 课程 baseline 与“检索策略”的关系

| Baseline | 输入形式 | 本质 |
|---|---|---|
| `simple` | `sys prompt + user query` | 无检索基线（只依赖模型参数知识） |
| `medium` | `sys prompt + user query + chunks(BM25)` | 稀疏检索策略（关键词/BM25） |
| `strong` | `sys prompt + user query + chunks(embedding)` | 稠密检索策略（向量相似度） |
| `boss` | 与 `medium/strong` 一致，但提高 chunk 数量 | 检索参数升级（如更大的 `top-k`），不一定是新算法 |

结论：这些 baseline 不只是 prompt 差异，更是“检索路径 + 参数配置”的差异。

### 13.2 切分策略：规则生成 vs 切分器

| 策略 | 类型 | 说明 |
|---|---|---|
| 固定 token + overlap | 切分器 | 典型参数化切分（`chunk_size/chunk_overlap`） |
| 递归切分（章/节/段/句） | 切分器 | 超长文本逐层降级切分 |
| 结构化切分（标题/表格/FAQ） | 规则为主 + 切分器 | 先按文档结构规则分段，再切块 |
| 语义切分 | 切分器（模型驱动） | 基于句向量相似度变化点断开 |
| 多粒度索引 | 策略层 | 组合多个切分结果（small/parent）联合召回 |
| 实体中心切分 | 规则/KG 为主 | 围绕实体与关系聚合证据块 |
| 查询时动态切分 | 策略层 | 检索时按 query 触发二次局部切分 |
| 时间/版本切分 | 规则分片 | 按生效时间、版本号管理知识片段 |

补充：当前 `scripts/build_kg_rag_dataset.py` 采用的是“每条 Fact 生成一条 chunk”的构造方式，不是通用自动切分器。

### 13.3 召回率（Recall）定义与调参意义

常用定义：`Recall@k = top-k 中命中的相关证据数 / 全部相关证据数`。

在 RAG 中，召回率会直接影响检索策略改动：

1. 召回低：优先优化检索（hybrid、query rewrite、实体别名扩展、`top-k`）。
2. 召回高但答案差：通常问题在 rerank、上下文组装或生成阶段。
3. 盲目增大 `top-k` 会引入噪声：需配合重排与上下文裁剪。

### 13.4 术语速查（非参数名词）

| 术语 | 解释 |
|---|---|
| `hybrid` | 混合检索，组合稀疏检索（BM25）与稠密检索（embedding） |
| `query rewrite` | 查询改写，把用户问题转为更利于检索的表达 |
| `entity expansion` | 实体扩展，基于别名/同义映射扩展检索种子 |
| `rerank` | 对初步召回结果再次打分重排，提升前排证据质量 |
| `KG` | 知识图谱（Graph），是实体-关系图结构，不是图片数据 |
| `top-k` | 检索阶段输入参数，表示最多保留前 k 条候选 |

### 13.5 为什么升级到“多粒度 + KG 实体中心”

相对“1 fact -> 1 chunk”的简单构造，主要提升点：

1. 召回更稳：小块提命中率，大块补上下文完整性。
2. 多跳更强：可由实体命中后沿关系边扩展证据链。
3. 可解释性更强：可给出实体/三元组/证据块的链路依据。
4. 可扩展性更好：便于后续叠加 rerank、时效过滤与权限策略。
