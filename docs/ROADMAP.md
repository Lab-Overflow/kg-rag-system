# Roadmap

## v0.1 · Demo (本仓库)
- [x] FastAPI + LangGraph Agent 骨架
- [x] Neo4j + Qdrant + Redis 全栈 docker-compose
- [x] 混合检索 + 社区摘要
- [x] 3D 图谱前端 + 对话
- [x] MCP Server
- [x] RAGAS 评估脚本

## v0.2 · 多模态（+1 月）
- [ ] ColPali PDF 视觉检索
- [ ] 音视频转写 + 时间戳 KG
- [ ] 图表数据抽取（Donut/LayoutLMv3）

## v0.3 · 时序与推理（+2 月）
- [ ] Bitemporal KG（valid-time/system-time）
- [ ] 因果/反事实子图检索
- [ ] 可解释答案：生成推理链 DAG

## v0.5 · 自优化
- [ ] 用户反馈 → 弱监督抽取器微调（DPO）
- [ ] 主动学习：Critic 触发人工标注队列
- [ ] A/B 检索策略自动实验

## v1.0 · Serverless + 联邦
- [ ] Lambda/Cloud Run 化的无状态组件
- [ ] 向量与图的 bring-your-own-storage 模式
- [ ] 跨组织 MCP 联邦 + 零信任鉴权
