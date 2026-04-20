"""Build a call-ready KG-RAG dataset (Hong Lou Meng themed) from scratch.

Outputs:
- chunks.jsonl
- triples.jsonl
- entity_alias.json
- test_public.jsonl
- test_private.jsonl
- hongloumeng_fulltext.txt (fallback for plain text chunking)
- manifest.json
- README.md
- rag_kg_hongloumeng_v1.zip
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import zipfile


@dataclass(frozen=True)
class Fact:
    fact_id: str
    head: str
    relation: str
    tail: str


ALIASES: dict[str, list[str]] = {
    "贾宝玉": ["宝玉", "怡红公子", "通灵宝玉主人"],
    "林黛玉": ["黛玉", "林妹妹", "潇湘妃子"],
    "薛宝钗": ["宝钗", "薛姑娘"],
    "王熙凤": ["凤姐", "凤辣子"],
    "贾琏": ["琏二爷"],
    "贾母": ["史太君", "老太太"],
    "贾政": ["政老爷"],
    "王夫人": ["二太太"],
    "贾赦": ["赦老爷"],
    "邢夫人": ["邢太太"],
    "贾珍": ["珍大爷"],
    "贾蓉": ["蓉哥儿"],
    "秦可卿": ["可卿"],
    "尤氏": ["尤大奶奶"],
    "袭人": ["花袭人"],
    "晴雯": ["晴姑娘"],
    "紫鹃": ["鹃儿"],
    "平儿": ["平姑娘"],
    "鸳鸯": ["老太太的鸳鸯"],
    "李纨": ["李宫裁"],
    "史湘云": ["湘云", "云妹妹"],
    "薛姨妈": ["薛王氏"],
    "薛蟠": ["文龙"],
    "贾探春": ["探春", "三姑娘"],
    "贾迎春": ["迎春", "二姑娘"],
    "妙玉": ["妙玉师太"],
    "刘姥姥": ["刘老老"],
    "荣国府": ["荣府"],
    "宁国府": ["宁府"],
    "大观园": ["园子"],
    "怡红院": ["怡红院落"],
    "潇湘馆": ["潇湘馆舍"],
    "蘅芜苑": ["蘅芜院"],
    "稻香村": ["稻香村院"],
    "栊翠庵": ["栊翠寺"],
    "元妃省亲": ["省亲"],
    "建造大观园": ["造园"],
    "抄检大观园": ["抄检"],
    "刘姥姥进大观园": ["刘姥姥游园"],
    "宝玉挨打": ["挨打事件"],
    "黛玉葬花": ["葬花"],
    "金玉良缘": ["金玉"],
    "木石前盟": ["木石"],
}


FACTS: list[Fact] = [
    Fact("F001", "贾宝玉", "父亲", "贾政"),
    Fact("F002", "贾宝玉", "母亲", "王夫人"),
    Fact("F003", "贾政", "配偶", "王夫人"),
    Fact("F004", "贾宝玉", "祖母", "贾母"),
    Fact("F005", "林黛玉", "外祖母", "贾母"),
    Fact("F006", "林黛玉", "父亲", "林如海"),
    Fact("F007", "林黛玉", "母亲", "贾敏"),
    Fact("F008", "贾敏", "兄长", "贾政"),
    Fact("F009", "贾赦", "兄长", "贾政"),
    Fact("F010", "贾琏", "父亲", "贾赦"),
    Fact("F011", "贾琏", "配偶", "王熙凤"),
    Fact("F012", "王熙凤", "管理", "荣国府"),
    Fact("F013", "王熙凤", "协理", "宁国府"),
    Fact("F014", "贾珍", "居住", "宁国府"),
    Fact("F015", "尤氏", "配偶", "贾珍"),
    Fact("F016", "贾蓉", "父亲", "贾珍"),
    Fact("F017", "秦可卿", "配偶", "贾蓉"),
    Fact("F018", "贾宝玉", "居住", "怡红院"),
    Fact("F019", "林黛玉", "居住", "潇湘馆"),
    Fact("F020", "薛宝钗", "居住", "蘅芜苑"),
    Fact("F021", "李纨", "居住", "稻香村"),
    Fact("F022", "史湘云", "暂住", "大观园"),
    Fact("F023", "怡红院", "位于", "大观园"),
    Fact("F024", "潇湘馆", "位于", "大观园"),
    Fact("F025", "蘅芜苑", "位于", "大观园"),
    Fact("F026", "稻香村", "位于", "大观园"),
    Fact("F027", "栊翠庵", "位于", "大观园"),
    Fact("F028", "大观园", "包含", "怡红院"),
    Fact("F029", "大观园", "包含", "潇湘馆"),
    Fact("F030", "大观园", "包含", "蘅芜苑"),
    Fact("F031", "大观园", "包含", "稻香村"),
    Fact("F032", "袭人", "侍奉", "贾宝玉"),
    Fact("F033", "晴雯", "侍奉", "贾宝玉"),
    Fact("F034", "紫鹃", "侍奉", "林黛玉"),
    Fact("F035", "平儿", "侍奉", "王熙凤"),
    Fact("F036", "鸳鸯", "侍奉", "贾母"),
    Fact("F037", "元妃省亲", "发生在", "大观园"),
    Fact("F038", "建造大观园", "原因", "元妃省亲"),
    Fact("F039", "黛玉葬花", "发生在", "沁芳桥畔"),
    Fact("F040", "沁芳桥畔", "位于", "大观园"),
    Fact("F041", "宝玉挨打", "执行者", "贾政"),
    Fact("F042", "宝玉挨打", "原因", "结交优伶"),
    Fact("F043", "抄检大观园", "影响", "晴雯"),
    Fact("F044", "抄检大观园", "影响", "司棋"),
    Fact("F045", "抄检大观园", "发生在", "大观园"),
    Fact("F046", "刘姥姥进大观园", "发生在", "大观园"),
    Fact("F047", "通灵宝玉", "属于", "贾宝玉"),
    Fact("F048", "木石前盟", "主角", "贾宝玉"),
    Fact("F049", "木石前盟", "主角", "林黛玉"),
    Fact("F050", "金玉良缘", "主角", "贾宝玉"),
    Fact("F051", "金玉良缘", "主角", "薛宝钗"),
    Fact("F052", "薛宝钗", "母亲", "薛姨妈"),
    Fact("F053", "薛蟠", "妹妹", "薛宝钗"),
    Fact("F054", "薛姨妈", "姐妹", "王夫人"),
    Fact("F055", "贾探春", "妹妹", "贾宝玉"),
    Fact("F056", "贾迎春", "姐姐", "贾宝玉"),
    Fact("F057", "妙玉", "居住", "栊翠庵"),
    Fact("F058", "王熙凤", "信任", "平儿"),
    Fact("F059", "晴雯", "判词", "心比天高"),
    Fact("F060", "袭人", "判词", "温柔和顺"),
    Fact("F061", "贾府衰落", "征兆", "抄检大观园"),
    Fact("F062", "贾府衰落", "征兆", "财政亏空"),
    Fact("F063", "宁国府", "同属", "贾府"),
    Fact("F064", "荣国府", "同属", "贾府"),
    Fact("F065", "贾宝玉", "表妹", "林黛玉"),
    Fact("F066", "薛宝钗", "亲戚", "贾宝玉"),
    Fact("F067", "史湘云", "亲戚", "贾宝玉"),
    Fact("F068", "王熙凤", "身份", "贾府管家"),
]


SENTENCE_TEMPLATES: dict[str, str] = {
    "父亲": "在《红楼梦》中，{head}的父亲是{tail}。",
    "母亲": "在《红楼梦》中，{head}的母亲是{tail}。",
    "配偶": "在《红楼梦》中，{head}的配偶是{tail}。",
    "祖母": "在《红楼梦》中，{head}的祖母是{tail}。",
    "外祖母": "在《红楼梦》中，{head}的外祖母是{tail}。",
    "兄长": "在《红楼梦》中，{head}的兄长是{tail}。",
    "姐姐": "在《红楼梦》中，{head}的姐姐是{tail}。",
    "妹妹": "在《红楼梦》中，{head}的妹妹是{tail}。",
    "居住": "在《红楼梦》中，{head}居住在{tail}。",
    "暂住": "在《红楼梦》中，{head}曾暂住于{tail}。",
    "位于": "在《红楼梦》中，{head}位于{tail}。",
    "包含": "在《红楼梦》中，{head}包含{tail}。",
    "管理": "在《红楼梦》中，{head}负责管理{tail}。",
    "协理": "在《红楼梦》中，{head}曾协理{tail}事务。",
    "侍奉": "在《红楼梦》中，{head}侍奉{tail}。",
    "发生在": "在《红楼梦》中，{head}发生在{tail}。",
    "原因": "在《红楼梦》中，{head}的原因与{tail}有关。",
    "执行者": "在《红楼梦》中，{head}的执行者是{tail}。",
    "影响": "在《红楼梦》中，{head}影响了{tail}。",
    "属于": "在《红楼梦》中，{head}属于{tail}。",
    "主角": "在《红楼梦》中，{head}的主角之一是{tail}。",
    "判词": "在《红楼梦》中，{head}的判词常被概括为“{tail}”。",
    "征兆": "在《红楼梦》中，{head}的征兆之一是{tail}。",
    "同属": "在《红楼梦》中，{head}与{tail}同属同一大家族体系。",
    "表妹": "在《红楼梦》中，{head}的表妹是{tail}。",
    "亲戚": "在《红楼梦》中，{head}与{tail}是亲戚关系。",
    "身份": "在《红楼梦》中，{head}的身份可以概括为{tail}。",
    "信任": "在《红楼梦》中，{head}十分信任{tail}。",
    "姐妹": "在《红楼梦》中，{head}与{tail}是姐妹关系。",
}


SINGLE_HOP_QUESTION_TEMPLATES: dict[str, str] = {
    "父亲": "{head}的父亲是谁？",
    "母亲": "{head}的母亲是谁？",
    "配偶": "{head}的配偶是谁？",
    "祖母": "{head}的祖母是谁？",
    "外祖母": "{head}的外祖母是谁？",
    "兄长": "{head}的兄长是谁？",
    "姐姐": "{head}的姐姐是谁？",
    "妹妹": "{head}的妹妹是谁？",
    "居住": "{head}居住在哪里？",
    "暂住": "{head}曾暂住在哪里？",
    "位于": "{head}位于哪里？",
    "包含": "{head}包含哪些地点之一？",
    "管理": "谁负责管理{tail}？",
    "协理": "谁曾协理{tail}事务？",
    "侍奉": "{head}侍奉谁？",
    "发生在": "{head}发生在哪里？",
    "原因": "{head}的原因是什么？",
    "执行者": "{head}的执行者是谁？",
    "影响": "{head}影响了谁？",
    "属于": "{head}属于谁？",
    "主角": "{head}的主角之一是谁？",
    "判词": "{head}的判词常被概括为什么？",
    "征兆": "{head}的征兆之一是什么？",
    "同属": "{head}与谁同属同一大家族体系？",
    "表妹": "{head}的表妹是谁？",
    "亲戚": "{head}与谁是亲戚关系？",
    "身份": "{head}的身份是什么？",
    "信任": "{head}信任谁？",
    "姐妹": "{head}与谁是姐妹关系？",
}


PRIVATE_QUERIES: list[dict[str, object]] = [
    {
        "id": "PR001",
        "query": "王熙凤的配偶的父亲是谁？",
        "answer": "贾赦",
        "type": "multi_hop",
        "supporting_facts": ["F011", "F010"],
    },
    {
        "id": "PR002",
        "query": "林黛玉居住的馆舍位于哪里？",
        "answer": "大观园",
        "type": "multi_hop",
        "supporting_facts": ["F019", "F024"],
    },
    {
        "id": "PR003",
        "query": "薛宝钗居住的院落位于哪里？",
        "answer": "大观园",
        "type": "multi_hop",
        "supporting_facts": ["F020", "F025"],
    },
    {
        "id": "PR004",
        "query": "李纨居住的地方属于哪座园子？",
        "answer": "大观园",
        "type": "multi_hop",
        "supporting_facts": ["F021", "F026"],
    },
    {
        "id": "PR005",
        "query": "谁是贾宝玉母亲的姐妹？",
        "answer": "薛姨妈",
        "type": "multi_hop",
        "supporting_facts": ["F002", "F054"],
    },
    {
        "id": "PR006",
        "query": "受抄检大观园影响的晴雯原本侍奉谁？",
        "answer": "贾宝玉",
        "type": "multi_hop",
        "supporting_facts": ["F043", "F033"],
    },
    {
        "id": "PR007",
        "query": "导致晴雯受影响的事件发生在哪里？",
        "answer": "大观园",
        "type": "multi_hop",
        "supporting_facts": ["F043", "F045"],
    },
    {
        "id": "PR008",
        "query": "宝玉挨打这一事件的执行者是谁？",
        "answer": "贾政",
        "type": "event_reasoning",
        "supporting_facts": ["F041"],
    },
    {
        "id": "PR009",
        "query": "促成建造大观园的关键事件是什么？",
        "answer": "元妃省亲",
        "type": "event_reasoning",
        "supporting_facts": ["F038"],
    },
    {
        "id": "PR010",
        "query": "发生在沁芳桥畔的事件位于哪座园子？",
        "answer": "大观园",
        "type": "multi_hop",
        "supporting_facts": ["F039", "F040"],
    },
    {
        "id": "PR011",
        "query": "与木石前盟对应的两位主角中，除贾宝玉外还有谁？",
        "answer": "林黛玉",
        "type": "aggregation",
        "supporting_facts": ["F048", "F049"],
    },
    {
        "id": "PR012",
        "query": "与金玉良缘对应的两位主角中，除贾宝玉外还有谁？",
        "answer": "薛宝钗",
        "type": "aggregation",
        "supporting_facts": ["F050", "F051"],
    },
    {
        "id": "PR013",
        "query": "王熙凤管理的府邸与贾珍居住的府邸分别是什么？",
        "answer": "荣国府与宁国府",
        "type": "comparison",
        "supporting_facts": ["F012", "F014"],
    },
    {
        "id": "PR014",
        "query": "贾宝玉居住在怡红院，而怡红院位于哪里？",
        "answer": "大观园",
        "type": "multi_hop",
        "supporting_facts": ["F018", "F023"],
    },
    {
        "id": "PR015",
        "query": "妙玉居住在栊翠庵，而栊翠庵位于哪里？",
        "answer": "大观园",
        "type": "multi_hop",
        "supporting_facts": ["F057", "F027"],
    },
    {
        "id": "PR016",
        "query": "平儿侍奉谁，而谁又信任平儿？",
        "answer": "王熙凤",
        "type": "multi_hop",
        "supporting_facts": ["F035", "F058"],
    },
    {
        "id": "PR017",
        "query": "宁国府和荣国府同属哪一个大家族体系？",
        "answer": "贾府",
        "type": "aggregation",
        "supporting_facts": ["F063", "F064"],
    },
    {
        "id": "PR018",
        "query": "刘姥姥进大观园这一事件发生在什么地点？",
        "answer": "大观园",
        "type": "event_reasoning",
        "supporting_facts": ["F046"],
    },
    {
        "id": "PR019",
        "query": "贾宝玉的母亲是王夫人，那么王夫人的配偶是谁？",
        "answer": "贾政",
        "type": "multi_hop",
        "supporting_facts": ["F002", "F003"],
    },
    {
        "id": "PR020",
        "query": "薛宝钗的母亲是谁，而这位人物与王夫人是什么关系？",
        "answer": "薛姨妈，与王夫人是姐妹",
        "type": "multi_hop",
        "supporting_facts": ["F052", "F054"],
    },
]


def sentence_for_fact(f: Fact) -> str:
    template = SENTENCE_TEMPLATES.get(f.relation, "在《红楼梦》中，{head}与{tail}存在{relation}关系。")
    return template.format(head=f.head, tail=f.tail, relation=f.relation)


def relation_question(f: Fact) -> str | None:
    template = SINGLE_HOP_QUESTION_TEMPLATES.get(f.relation)
    if not template:
        return None
    return template.format(head=f.head, tail=f.tail)


def answer_for_fact(f: Fact) -> str:
    # Most templates ask for tail, except role-reversed templates.
    if f.relation in {"管理", "协理"}:
        return f.head
    return f.tail


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_dataset(out_dir: Path) -> None:
    ensure_dir(out_dir)

    facts_by_id: dict[str, Fact] = {f.fact_id: f for f in FACTS}
    chunks: list[dict] = []
    triples: list[dict] = []
    public_queries: list[dict] = []

    for idx, fact in enumerate(FACTS, start=1):
        chunk_id = f"chunk_{idx:04d}"
        triple_id = f"triple_{idx:04d}"
        text = sentence_for_fact(fact)
        chunks.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "source": "curated_hongloumeng_v1",
                "entities": [fact.head, fact.tail],
                "fact_id": fact.fact_id,
            }
        )
        triples.append(
            {
                "triple_id": triple_id,
                "head": fact.head,
                "relation": fact.relation,
                "tail": fact.tail,
                "evidence_chunk_ids": [chunk_id],
                "confidence": 1.0,
                "source": "manual_curated_v1",
                "fact_id": fact.fact_id,
            }
        )

        q = relation_question(fact)
        if q is not None:
            public_queries.append(
                {
                    "id": f"PU{idx:03d}",
                    "query": q,
                    "answer": answer_for_fact(fact),
                    "type": "single_hop",
                    "supporting_facts": [fact.fact_id],
                }
            )

    # keep public set concise and readable
    public_queries = public_queries[:48]

    # Enrich private query rows with triple ids and chunk ids for downstream checks
    fact_to_triple = {t["fact_id"]: t["triple_id"] for t in triples}
    fact_to_chunk = {c["fact_id"]: c["chunk_id"] for c in chunks}
    private_queries: list[dict] = []
    for row in PRIVATE_QUERIES:
        supports = list(row["supporting_facts"])
        private_queries.append(
            {
                **row,
                "supporting_triples": [fact_to_triple[fid] for fid in supports if fid in fact_to_triple],
                "supporting_chunk_ids": [fact_to_chunk[fid] for fid in supports if fid in fact_to_chunk],
            }
        )

    # add same helper fields to public queries
    for row in public_queries:
        supports = list(row["supporting_facts"])
        row["supporting_triples"] = [fact_to_triple[fid] for fid in supports if fid in fact_to_triple]
        row["supporting_chunk_ids"] = [fact_to_chunk[fid] for fid in supports if fid in fact_to_chunk]

    write_jsonl(out_dir / "chunks.jsonl", chunks)
    write_jsonl(out_dir / "triples.jsonl", triples)
    write_jsonl(out_dir / "test_public.jsonl", public_queries)
    write_jsonl(out_dir / "test_private.jsonl", private_queries)

    with (out_dir / "entity_alias.json").open("w", encoding="utf-8") as fp:
        json.dump(ALIASES, fp, ensure_ascii=False, indent=2)

    # fallback full text
    with (out_dir / "hongloumeng_fulltext.txt").open("w", encoding="utf-8") as fp:
        for row in chunks:
            fp.write(row["text"] + "\n")

    manifest = {
        "dataset_name": "rag_kg_hongloumeng_v1",
        "version": "1.0.0",
        "language": "zh-CN",
        "source": "manual_curated",
        "counts": {
            "chunks": len(chunks),
            "triples": len(triples),
            "public_queries": len(public_queries),
            "private_queries": len(private_queries),
            "alias_entities": len(ALIASES),
        },
        "relations": sorted({f.relation for f in FACTS}),
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as fp:
        json.dump(manifest, fp, ensure_ascii=False, indent=2)

    readme = """# rag_kg_hongloumeng_v1

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
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    zip_path = out_dir / "rag_kg_hongloumeng_v1.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(out_dir.glob("*")):
            if file.name == zip_path.name:
                continue
            zf.write(file, arcname=file.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build KG-RAG dataset artifacts.")
    parser.add_argument(
        "--out-dir",
        default="data/rag_kg_hongloumeng_v1",
        help="Output directory for dataset files.",
    )
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    build_dataset(out_dir)
    print(f"[OK] Dataset generated at: {out_dir}")


if __name__ == "__main__":
    main()
