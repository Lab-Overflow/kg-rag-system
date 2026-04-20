# Baseline Difference & Direct-Call Smoke Report

## 1) Direct call smoke (website subpage simulation)

| File | Status | Detail |
|---|---|---|
| `test_public.jsonl` | PASS | status=200, bytes=10062 |
| `test_private.jsonl` | PASS | status=200, bytes=5359 |
| `chunks.jsonl` | PASS | status=200, bytes=13003 |
| `triples.jsonl` | PASS | status=200, bytes=13612 |
| `entity_alias.json` | PASS | status=200, bytes=1791 |
| `manifest.json` | PASS | status=200, bytes=690 |

## 2) Baseline comparison (Simple vs Medium vs Strong vs Boss)

| Split | Simple | Medium | Strong | Boss |
|---|---:|---:|---:|---:|
| public | 0.00% | 100.00% | 100.00% | 100.00% |
| private | 0.00% | 80.00% | 100.00% | 100.00% |
| all | 0.00% | 94.12% | 100.00% | 100.00% |

## 3) Input & Output examples (before/after)

### PU001
- Input: `贾宝玉的父亲是谁？`
- Gold: `贾政`
- Simple output (no RAG): `证据不足`
- Medium output (text RAG): `贾政`
- Strong output (text + KG): `贾政`
- Boss output (extended text + KG): `贾政`
- Delta: simple→strong = `False`→`True`, simple→boss = `False`→`True`

### PU002
- Input: `贾宝玉的母亲是谁？`
- Gold: `王夫人`
- Simple output (no RAG): `证据不足`
- Medium output (text RAG): `王夫人`
- Strong output (text + KG): `王夫人`
- Boss output (extended text + KG): `王夫人`
- Delta: simple→strong = `False`→`True`, simple→boss = `False`→`True`

### PU003
- Input: `贾政的配偶是谁？`
- Gold: `王夫人`
- Simple output (no RAG): `证据不足`
- Medium output (text RAG): `王夫人`
- Strong output (text + KG): `王夫人`
- Boss output (extended text + KG): `王夫人`
- Delta: simple→strong = `False`→`True`, simple→boss = `False`→`True`

### PR001
- Input: `王熙凤的配偶的父亲是谁？`
- Gold: `贾赦`
- Simple output (no RAG): `证据不足`
- Medium output (text RAG): `贾赦`
- Strong output (text + KG): `贾赦`
- Boss output (extended text + KG): `贾赦`
- Delta: simple→strong = `False`→`True`, simple→boss = `False`→`True`

### PR002
- Input: `林黛玉居住的馆舍位于哪里？`
- Gold: `大观园`
- Simple output (no RAG): `证据不足`
- Medium output (text RAG): `证据不足`
- Strong output (text + KG): `大观园`
- Boss output (extended text + KG): `大观园`
- Delta: simple→strong = `False`→`True`, simple→boss = `False`→`True`

### PR003
- Input: `薛宝钗居住的院落位于哪里？`
- Gold: `大观园`
- Simple output (no RAG): `证据不足`
- Medium output (text RAG): `证据不足`
- Strong output (text + KG): `大观园`
- Boss output (extended text + KG): `大观园`
- Delta: simple→strong = `False`→`True`, simple→boss = `False`→`True`
