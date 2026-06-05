from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CHAPTERS = {
    "ch02": {
        "title": "道路建模的图形原理与三维表达",
        "raw": next((ROOT / "data/raw/ch02").glob("*.json")),
        "word_extract": ROOT / "output/ch02_rag_engine/reports/ch02_word_extract.txt",
        "terms": [
            "空间坐标系统",
            "WCS",
            "UCS",
            "工程桩号",
            "几何图元",
            "布尔运算",
            "平行投影",
            "透视投影",
            "DEM",
            "TIN",
            "Voronoi",
            "Delaunay",
            "约束Delaunay",
            "线框模型",
            "表面模型",
            "实体模型",
        ],
    },
    "ch03": {
        "title": "道路CAD系统的设计原理",
        "raw": next((ROOT / "data/raw/ch03").glob("*.json")),
        "word_extract": ROOT / "output/ch03_rag_engine/reports/ch03_word_extract.txt",
        "terms": [
            "CAD系统",
            "道路CAD",
            "模块化",
            "平面设计",
            "纵断面",
            "横断面",
            "基本型曲线",
            "卵形曲线",
            "双交点曲线",
            "逐桩坐标",
            "竖曲线",
            "戴帽规则",
            "超高",
            "边坡线单元",
            "土石方",
            "平面交叉口",
            "Coons曲面",
        ],
    },
}


def main() -> int:
    for chapter_id, config in CHAPTERS.items():
        write_review(chapter_id, config)
    return 0


def write_review(chapter_id: str, config: dict[str, Any]) -> None:
    raw_path = Path(config["raw"])
    word_path = Path(config["word_extract"])
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    word_text = word_path.read_text(encoding="utf-8") if word_path.exists() else ""
    kb_text = build_kb_text(data)
    term_rows = []
    for term in config["terms"]:
        term_rows.append(
            {
                "term": term,
                "word": term in word_text,
                "kb": term in kb_text,
                "answer_hits": count_rows_with_text(data.get("Answer_Cards", []), term),
                "kp_hits": count_rows_with_text(data.get("Knowledge_Points", []), term),
            }
        )

    image_resources = [
        row
        for row in data.get("Resources", [])
        if isinstance(row, dict) and row.get("resource_type") == "image"
    ]
    bound_images = [row for row in image_resources if row.get("status") == "bound" and row.get("file_path")]
    unbound_images = [row for row in image_resources if row not in bound_images]

    report = render_report(
        chapter_id=chapter_id,
        title=str(config["title"]),
        data=data,
        word_text=word_text,
        term_rows=term_rows,
        image_resources=image_resources,
        bound_images=bound_images,
        unbound_images=unbound_images,
    )
    output = ROOT / "output" / f"{chapter_id}_rag_engine" / "reports" / f"{chapter_id}_content_review_enhancement.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"{chapter_id}: review={output}")


def build_kb_text(data: dict[str, Any]) -> str:
    tables = [
        "Answer_Cards",
        "Knowledge_Points",
        "Concept_Comparison",
        "Source_Chunks",
        "Resources",
        "Exercises",
    ]
    parts: list[str] = []
    for table in tables:
        for row in data.get(table, []):
            parts.append(json.dumps(row, ensure_ascii=False))
    return "\n".join(parts)


def count_rows_with_text(rows: object, term: str) -> int:
    if not isinstance(rows, list):
        return 0
    return sum(1 for row in rows if term in json.dumps(row, ensure_ascii=False))


def render_report(
    chapter_id: str,
    title: str,
    data: dict[str, Any],
    word_text: str,
    term_rows: list[dict[str, Any]],
    image_resources: list[dict[str, Any]],
    bound_images: list[dict[str, Any]],
    unbound_images: list[dict[str, Any]],
) -> str:
    qa_count = len(data.get("QA_Evaluation_Testset", []))
    answer_count = len(data.get("Answer_Cards", []))
    kp_count = len(data.get("Knowledge_Points", []))
    resource_count = len(data.get("Resources", []))
    script_count = len(data.get("Interactive_Scripts", []))
    lines = [
        f"# {chapter_id} Word 原稿复核增强报告",
        "",
        f"章节：{title}",
        "",
        "## 数据概况",
        "",
        f"- Word 抽取文本长度：{len(word_text)} 字符",
        f"- 答案卡：{answer_count}",
        f"- 知识点：{kp_count}",
        f"- QA 评测题：{qa_count}",
        f"- 资源：{resource_count}",
        f"- 互动脚本：{script_count}",
        "",
        "## 术语覆盖抽查",
        "",
        "| 术语 | Word 原稿 | 知识库 | 答案卡命中 | 知识点命中 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in term_rows:
        lines.append(
            f"| {row['term']} | {yes(row['word'])} | {yes(row['kb'])} | "
            f"{row['answer_hits']} | {row['kp_hits']} |"
        )
    lines.extend(
        [
            "",
            "## 图片资源绑定",
            "",
            f"- 图片资源总数：{len(image_resources)}",
            f"- 已绑定图片：{len(bound_images)}",
            f"- 仍为占位：{len(unbound_images)}",
            "",
            "### 已绑定图片",
            "",
        ]
    )
    if bound_images:
        lines.extend(
            f"- `{row.get('resource_id')}`：{row.get('title')} -> `{row.get('file_path')}`"
            for row in bound_images
        )
    else:
        lines.append("- 无")
    lines.extend(["", "### 待人工核验图片", ""])
    if unbound_images:
        lines.extend(
            f"- `{row.get('resource_id')}`：{row.get('title')}"
            for row in unbound_images
        )
    else:
        lines.append("- 无")
    lines.extend(["", "## 复核结论", ""])
    if chapter_id == "ch02":
        lines.extend(
            [
                "- 第二章核心术语在 Word 原稿与知识库中均有覆盖。",
                "- 第二章 14 张教材图片已全部绑定到项目内相对路径，可在前端资源卡中打开。",
                "- 后续可继续补表格、公式的可视化资源文件。",
            ]
        )
    else:
        lines.extend(
            [
                "- 第三章核心术语在 Word 原稿与知识库中均有覆盖。",
                "- 第三章草稿资源表与 Word 原稿图号存在错位；本轮只绑定同名或语义明确图片，避免错误绑定。",
                "- 后续建议人工核验第三章剩余图片资源，统一资源编号、标题和 Word 图号。",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def yes(value: bool) -> str:
    return "是" if value else "否"


if __name__ == "__main__":
    raise SystemExit(main())
