# Architecture · 深度说明

## 1. 数据流全景

```
Source(PDF/HTML/DB/API)
   │
   ▼ (1) Ingestion Pipeline  ─── Ray Actor Pool
   │   ├── Loader        (Unstructured / Docling / ColPali-ready)
   │   ├── Chunker       (Semantic split + proposition-level)
   │   ├── Embedder      (BGE-M3 dense + SPLADE sparse + ColBERT tokens)
   │   └── Extractor     (LLM JSON-schema → entities/relations/claims)
   │
   ▼ (2) Storage Writer
   │   ├── Qdrant        (dense + sparse hybrid collection)
   │   ├── Neo4j         (MERGE entity/relation, 属性 embedding)
   │   ├── OpenSearch    (BM25 fallback)
   │   └── Blob(S3/OSS)  (原文 + page thumbnails)
   │
   ▼ (3) KG Post-Processing   ─── 异步 Worker
   │   ├── Entity Resolution (embedding similarity + rule)
   │   ├── Leiden Community Detection (GDS)
   │   ├── Community Summarization (LLM map-reduce)
   │   └── PPR preprocess cache
   │
   ▼ (4) Query Time
       ├── Router          → 选模式
       ├── Retriever(s)    → Hybrid / Graph / ColBERT
       ├── Reranker        → Cohere rerank-v3 or bge-reranker-v2-m3
       ├── Context Builder → Dedup + token budget + citation tag
       ├── LangGraph Agent → Plan/Act/Reflect
       └── Answer + Citations + Subgraph payload
```

## 2. 关键组件选型与理由

### 2.1 图数据库：Neo4j 5 + GDS
- **选理由**：GDS 内置 Leiden/PPR/节点相似度，Cypher 生态成熟，社区/企业双版本。
- **替代**：Nebula Graph（更强分布式，适合 10 亿边级），Memgraph（内存型，低延迟实时）。
- **Schema**：`(:Entity {id, name, type, embedding, aliases})`，`[:REL {type, weight, evidence_chunk_ids, confidence}]`。

### 2.2 向量库：Qdrant
- 支持 **named vectors**（同一 point 存 dense + sparse + colbert tokens），减少多库来回。
- 支持 **scalar/binary quantization**，内存压缩 4-32×，P99 不明显劣化。
- 支持 shard + replica，payload 索引强于 Pinecone。

### 2.3 嵌入与重排
| 阶段 | 模型 | 备注 |
|---|---|---|
| Dense | `BAAI/bge-m3` | 多语言 + 8k 上下文 |
| Sparse | `naver/splade-v3` | 训练成本低，可替 BM25 |
| Late-interaction | `colbert-ir/colbertv2.0` 或 `colpali-v1.2` | 二阶段用 |
| Rerank | `cohere/rerank-v3.5` 或 `BAAI/bge-reranker-v2-m3` | Hosted vs 自托管 |

### 2.4 LLM 路由
- **默认 Planner**：Claude Opus 4（复杂推理）
- **Extractor/Summarizer**：Claude Haiku 4.5 或 Qwen 3-32B（便宜 + 结构化）
- **兜底本地**：Ollama + Qwen3-14B（离线、合规场景）
- 所有调用走 **LiteLLM Proxy** 实现统一 key/计费/限流。

## 3. LangGraph Agent 拓扑

```
          ┌──────────┐
          │  Start   │
          └────┬─────┘
               ▼
        ┌──────────────┐
        │   Planner    │──(trivial)──▶ direct retrieve
        └────┬─────────┘
             │ plan = [subq1, subq2, ...]
             ▼
     ┌─────────────────┐          ┌─────────────────┐
     │  Retriever Hub  │─────────▶│  Context Builder│
     │ (parallel)      │          └────────┬────────┘
     └─────────────────┘                   ▼
                                    ┌────────────┐
                                    │  Synthesize│
                                    └─────┬──────┘
                                          ▼
                                    ┌────────────┐
                                    │   Critic   │──sufficient──▶ END
                                    └─────┬──────┘
                                          │ insufficient (k<3)
                                          └─────▶ re-plan
```
- 带 **checkpointer**（Redis 或 Postgres），可断点续跑。
- 最大反思轮次可配（默认 3），超出直接返回当前最佳答案 + warning。

## 4. 可扩展性：压力曲线与应对

| 负载维度 | 瓶颈 | 缓解 |
|---|---|---|
| 文档灌入 QPS | LLM 抽取延迟 | Ray Actor Pool 横向扩；小模型批量；按租户配额 |
| 查询 QPS | 重排 GPU | 独立 rerank microservice + KEDA 按队列深度扩缩 |
| Neo4j 写放大 | 批量 UNWIND + PERIODIC COMMIT；大图切换到 Nebula |
| Qdrant 内存 | 开启 Scalar Quant + on-disk；冷热双 collection |
| LLM 上下文 | 上下文压缩（LLMLingua-2）；层级摘要替代全文 |
| 成本 | 语义缓存（Redis + embedding similarity）；small-first 路由 |

## 5. 观测与调优

- **OpenTelemetry**：所有 span 带 `request_id, tenant, mode, retriever, token_in/out, latency`。
- **Phoenix**：LLM trace 回放 + 数据集 vs 回归对比。
- **LangFuse**：生产线上日志沉淀，支持对单轮 session 打标签。
- **Grafana**：检索召回率、Faithfulness 滑窗、RAGAS 分位。

## 6. 安全与合规

- 租户隔离：JWT claim → Neo4j 子图 + Qdrant payload filter。
- PII 脱敏：Presidio 预处理；抽取后仍保留原文引用链路（受控访问）。
- Prompt 注入防护：
  - 输入 → GuardrailsAI 结构化校验；
  - 检索结果 → 标记 `[RETRIEVED]` 分隔符 + LLM side-channel 指令；
  - 输出 → 关键词 + 模型分类器双重过滤。
- 审计：所有查询与答案持久化（可合规导出）。

## 7. 未来扩展点

1. **GraphRAG on-line incremental**：目前社区摘要走离线批；可改为增量更新。
2. **Self-improving KG**：把用户反馈（👍/👎）作为弱监督，微调关系抽取器。
3. **Tool-former-style**：Agent 可以调用外部 SQL/搜索引擎/代码解释器，闭环到 KG。
4. **Temporal KG**：引入 bitemporal（valid-time, system-time），支持 "2024 Q3 时 X 的 CEO 是谁"。
5. **联邦 KG**：跨组织通过 MCP + 零知识证明交换子图。
