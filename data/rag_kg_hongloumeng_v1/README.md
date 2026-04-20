# rag_kg_hongloumeng_v1

可直接用于课程 notebook 的 KG-RAG 数据集（中文，红楼梦主题）。

## Files
- `test_public.jsonl`: 公开测试集（单跳为主）
- `test_private.jsonl`: 私有测试集（多跳/聚合/比较）
- `chunks.jsonl`: 文本检索 chunk 资产
- `triples.jsonl`: 知识图谱三元组（含证据 chunk id）
- `entity_alias.json`: 实体别名表
- `hongloumeng_fulltext.txt`: 兼容纯文本切块流程的回退文件
- `manifest.json`: 元信息与计数

## Suggested hosting path
将整个目录上传到你的网站子目录，例如：

`https://<your-domain>/rag-data/`

这样 notebook 可按文件名直接下载：
- `https://<your-domain>/rag-data/test_public.jsonl`
- `https://<your-domain>/rag-data/test_private.jsonl`
- `https://<your-domain>/rag-data/chunks.jsonl`
- `https://<your-domain>/rag-data/triples.jsonl`
- `https://<your-domain>/rag-data/entity_alias.json`
