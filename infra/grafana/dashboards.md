# Grafana 面板建议

导入 JSON 略；关键 panel：

1. **请求全景**：QPS / P50 / P95 / P99 按 mode 分组（`http_server_duration_seconds`）
2. **Agent 反思**：每条 agentic 请求的 round 数分布（`kg_rag.agent.rounds`）
3. **检索召回**：RAGAS faithfulness / context_precision 滑窗均值
4. **LLM 成本**：`kg_rag.llm.tokens_in/out` · 按租户分组，换算 USD
5. **KG 规模**：`kg_rag.kg.entities / relations / communities`
6. **向量库**：Qdrant 段数、quantization 命中率、P95 搜索时延
7. **错误**：按异常类型分桶（extractor 结构化失败率、Cypher timeout…）
