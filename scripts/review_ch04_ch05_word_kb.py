from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CHAPTERS = {
    "ch04": {
        "title": "道路BIM正向设计的原理与方法",
        "raw": next((ROOT / "data/raw/ch04").glob("*.json")),
        "terms": [
            "BIM定义",
            "道路BIM",
            "建筑BIM",
            "协同机制",
            "数据流转",
            "正向设计",
            "构件体系",
            "参数—规则—结果",
            "PPR",
            "参数化建模",
            "成果表达",
            "成果交付",
        ],
    },
    "ch05": {
        "title": "GIS理论基础与空间分析方法",
        "raw": next((ROOT / "data/raw/ch05").glob("*.json")),
        "terms": [
            "GIS定义",
            "空间问题",
            "地图投影",
            "低失真投影",
            "空间数据模型",
            "拓扑关系",
            "矢量空间分析",
            "栅格空间分析",
            "数字地形分析",
            "视域分析",
            "空间插值",
            "地统计",
            "网络分析",
        ],
    },
}


def main() -> int:
    for chapter_id, config in CHAPTERS.items():
        write_review(chapter_id, config)
    return 0


def write_review(chapter_id: str, config: dict[str, Any]) -> None:
    data = json.loads(Path(config["raw"]).read_text(encoding="utf-8"))
    word_path = ROOT / "output" / f"{chapter_id}_rag_engine" / "reports" / f"{chapter_id}_word_extract.txt"
    word_text = word_path.read_text(encoding="utf-8") if word_path.exists() else ""
    kb_text = build_kb_text(data)
    terms = []
    for term in config["terms"]:
        terms.append(
            {
                "term": term,
                "word": term in word_text,
                "kb": term in kb_text,
                "answer_hits": count_rows(data.get("Answer_Cards", []), term),
                "kp_hits": count_rows(data.get("Knowledge_Points", []), term),
            }
        )

    scripts = [
        row
        for row in data.get("Resources", [])
        if isinstance(row, dict) and row.get("resource_type") == "interactive_html"
    ]
    verification = data.get("metadata", {}).get("word_verification", {})
    lines = [
        f"# {chapter_id} Word正式稿复核与增强报告",
        "",
        f"章节：{config['title']}",
        "",
        "## 数据概况",
        "",
        f"- Word抽取文本：{len(word_text)} 字符",
        f"- 答案卡：{len(data.get('Answer_Cards', []))}",
        f"- 知识点：{len(data.get('Knowledge_Points', []))}",
        f"- QA评测题：{len(data.get('QA_Evaluation_Testset', []))}",
        f"- 资源：{len(data.get('Resources', []))}",
        f"- 互动脚本：{len(scripts)}",
        f"- Source_Chunks正式稿精确命中：{verification.get('exact', 0)}",
        f"- Source_Chunks正式稿部分命中：{verification.get('partial', 0)}",
        f"- Source_Chunks正式稿概念支持：{verification.get('concept_supported', 0)}",
        f"- Source_Chunks待复核：{verification.get('unverified', 0)}",
        "",
        "## 术语覆盖抽查",
        "",
        "| 术语 | Word正式稿 | 知识库 | 答案卡命中 | 知识点命中 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in terms:
        lines.append(
            f"| {row['term']} | {yes(row['word'])} | {yes(row['kb'])} | "
            f"{row['answer_hits']} | {row['kp_hits']} |"
        )
    lines.extend(
        [
            "",
            "## 互动脚本纳入情况",
            "",
        ]
    )
    lines.extend(
        f"- `{row.get('resource_id')}`：{row.get('title')} -> `{row.get('file_path')}`"
        for row in scripts
    )
    lines.extend(
        [
            "",
            "## 复核结论",
            "",
            "- 初稿已按项目统一表结构规范化，答案卡、知识点、评测题和检索配置可进入现有RAG链路。",
            "- Source_Chunks已增加正式Word文稿核验标记，未精确命中的片段保留为待复核项，不直接删除。",
            "- 互动脚本已作为可检索学习资源纳入，并与同节知识点及答案卡建立推荐关系。",
            "",
        ]
    )
    output = ROOT / "output" / f"{chapter_id}_rag_engine" / "reports" / f"{chapter_id}_content_review_enhancement.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"{chapter_id}: review={output}")


def build_kb_text(data: dict[str, Any]) -> str:
    tables = ["Answer_Cards", "Knowledge_Points", "Concept_Comparison", "Source_Chunks", "Resources", "Exercises"]
    return "\n".join(
        json.dumps(row, ensure_ascii=False)
        for table in tables
        for row in data.get(table, [])
    )


def count_rows(rows: object, term: str) -> int:
    if not isinstance(rows, list):
        return 0
    return sum(1 for row in rows if term in json.dumps(row, ensure_ascii=False))


def yes(value: bool) -> str:
    return "是" if value else "否"


if __name__ == "__main__":
    raise SystemExit(main())
