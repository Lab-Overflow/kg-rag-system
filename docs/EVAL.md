# Evaluation

## 离线基准

| 数据集 | 任务 | 指标 |
|---|---|---|
| **HotpotQA**（子集 1k） | 多跳 QA | EM / F1 |
| **MuSiQue** | 2–4 跳组合推理 | F1 |
| **2WikiMultihop** | 多跳 QA + 图谱适配 | EM / F1 |
| **自建 KG-Eval-300** | 实体抽取、关系抽取 | Precision / Recall / F1 |
| **Financial-RAG-Bench** | 研报问答（含表格） | Faithfulness / Relevance (RAGAS) |

脚本：`backend/app/eval/benchmark.py`，用法：

```bash
python -m app.eval.benchmark --dataset musique --mode agentic --limit 200
```

## 在线观测

- **RAGAS 实时**：每 100 条请求抽 1 条做在线评估（Claude Haiku 当 Judge），结果写 Prometheus。
- **点赞率**：前端 👍/👎 写回 LangFuse。
- **兜底率**：Critic 触发二次检索的占比。
- **成本/Query**：按租户/模式分桶。

## 压力测试

`scripts/locustfile.py` 覆盖：
- 混合负载：80% 简单查询 + 15% 多跳 + 5% Ingest
- 突发：10× 峰值持续 2 min，观察 HPA 反应
- 热数据倾斜：20% 实体占 80% 查询

SLO：
- P95 < 2.5s（hybrid mode）
- P95 < 6s（agentic mode, ≤3 rounds）
- Ingest 吞吐 ≥ 200 docs/min/worker
