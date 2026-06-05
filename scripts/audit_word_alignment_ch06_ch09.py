from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZipFile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCX = (
    Path("F:/")
    / "编书"
    / "道路工程数字设计方法"
    / "05脚本及图片素材"
    / "批注版-道路工程数字设计方法-数字化教材稿.docx"
)

CHAPTERS = {
    "ch06": {
        "title": "AutoCAD绘图基础与应用技巧",
        "start_any": ["AutoCAD绘图基础与应用技巧"],
        "end_any": ["道路CAD软件的使用"],
    },
    "ch07": {
        "title": "道路CAD软件的使用",
        "start_any": ["道路CAD软件的使用"],
        "end_any": ["OpenRoads Designer参数化架构", "道路BIM软件的使用"],
    },
    "ch08": {
        "title": "道路BIM软件的使用",
        "start_any": ["OpenRoads Designer参数化架构"],
        "end_any": ["道路正向设计中的BIM+GIS集成方法", "数据驱动的BIM+GIS道路设计范式"],
    },
    "ch09": {
        "title": "道路正向设计中的BIM+GIS集成方法",
        "start_any": ["道路正向设计中的BIM+GIS集成方法", "数据驱动的BIM+GIS道路设计范式"],
        "end_any": ["AI驱动的道路设计方法"],
    },
    "ch10": {
        "title": "AI驱动的道路设计方法",
        "start_any": ["AI驱动的道路设计方法"],
        "end_any": ["道路数字孪生的概念与方法体系"],
    },
    "ch11": {
        "title": "道路数字孪生的概念与方法体系",
        "start_any": ["道路数字孪生的概念与方法体系"],
        "end_any": [],
    },
}

WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
MIN_BODY_INDEX = 200


@dataclass
class Paragraph:
    index: int
    style: str
    text: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit chapter 6-11 KB rows against the textbook Word draft.")
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    parser.add_argument("--chapters", nargs="+", default=list(CHAPTERS), choices=sorted(CHAPTERS))
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "word_alignment_ch06_ch11_2026-06-04.json")
    args = parser.parse_args()

    paragraphs = extract_docx_paragraphs(args.docx)
    chapter_ranges = locate_chapter_ranges(paragraphs)
    reports = []
    for chapter_id in args.chapters:
        report = audit_chapter(chapter_id, paragraphs, chapter_ranges[chapter_id])
        reports.append(report)
        write_chapter_reports(chapter_id, report)

    summary = {
        "docx": str(args.docx),
        "chapters": [public_report(report) for report in reports],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "chapters": compact_summary(reports)}, ensure_ascii=False, indent=2))
    return 0


def extract_docx_paragraphs(docx_path: Path) -> list[Paragraph]:
    if not docx_path.exists():
        raise SystemExit(f"Word draft not found: {docx_path}")
    with ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))

    paragraphs: list[Paragraph] = []
    for xml_para in root.findall(".//w:p", WORD_NS):
        parts: list[str] = []
        for node in xml_para.iter():
            name = node.tag.rsplit("}", 1)[-1]
            if name == "t" and node.text:
                parts.append(node.text)
            elif name == "tab":
                parts.append("\t")
            elif name == "br":
                parts.append("\n")
        text = normalize_spaces("".join(parts))
        if not text:
            continue
        style = ""
        style_node = xml_para.find("./w:pPr/w:pStyle", WORD_NS)
        if style_node is not None:
            style = style_node.attrib.get(f"{{{WORD_NS['w']}}}val", "")
        paragraphs.append(Paragraph(index=len(paragraphs), style=style, text=text))
    return paragraphs


def locate_chapter_ranges(paragraphs: list[Paragraph]) -> dict[str, tuple[int, int]]:
    ranges: dict[str, tuple[int, int]] = {}
    for chapter_id, config in CHAPTERS.items():
        start = first_heading_index(paragraphs, config["start_any"])
        end = first_heading_index(paragraphs, config["end_any"], after=start + 1) if config.get("end_any") else len(paragraphs)
        ranges[chapter_id] = (start, end)
    return ranges


def first_heading_index(paragraphs: list[Paragraph], needles: list[str], after: int = MIN_BODY_INDEX) -> int:
    for para in paragraphs:
        if para.index < after:
            continue
        if para.style.upper().startswith("TOC"):
            continue
        if any(needle in para.text for needle in needles):
            return para.index
    raise SystemExit(f"Cannot locate chapter anchor: {needles}")


def audit_chapter(chapter_id: str, paragraphs: list[Paragraph], range_pair: tuple[int, int]) -> dict[str, Any]:
    start, end = range_pair
    chapter_paragraphs = [para for para in paragraphs if start <= para.index < end]
    word_text = "\n".join(para.text for para in chapter_paragraphs)
    compact_word_text = compact(word_text)

    raw_path = next((ROOT / "data/raw" / chapter_id).glob("*知识库*.json"))
    data = json.loads(raw_path.read_text(encoding="utf-8-sig"))
    kb_text = build_kb_text(data)
    compact_kb_text = compact(kb_text)

    source_rows = audit_source_chunks(data.get("Source_Chunks", []), compact_word_text)
    kp_rows = audit_terms(data.get("Knowledge_Points", []), "kp_id", "title", compact_word_text, kb_text)
    task_rows = audit_terms(data.get("Operation_Tasks", []), "task_id", "task_name", compact_word_text, kb_text)
    answer_rows = audit_answer_cards(data.get("Answer_Cards", []), compact_word_text)
    heading_rows = audit_headings(chapter_paragraphs, compact_kb_text)
    candidate_terms = extract_candidate_terms(word_text, kb_text)

    return {
        "chapter_id": chapter_id,
        "title": CHAPTERS[chapter_id]["title"],
        "raw_package": str(raw_path),
        "_word_text": word_text,
        "word_range": {"start_paragraph": start, "end_paragraph": end, "paragraphs": len(chapter_paragraphs)},
        "word_characters": len(word_text),
        "kb_counts": {
            "Knowledge_Points": len(data.get("Knowledge_Points", [])),
            "Answer_Cards": len(data.get("Answer_Cards", [])),
            "Source_Chunks": len(data.get("Source_Chunks", [])),
            "Operation_Tasks": len(data.get("Operation_Tasks", [])),
            "Operation_Steps": len(data.get("Operation_Steps", [])),
            "Common_Errors": len(data.get("Common_Errors", [])),
        },
        "source_chunk_alignment": summarize_status(source_rows),
        "knowledge_point_alignment": summarize_bool(kp_rows, "word_hit"),
        "operation_task_alignment": summarize_bool(task_rows, "word_hit"),
        "answer_card_alignment": summarize_bool(answer_rows, "word_hit"),
        "heading_coverage": summarize_bool(heading_rows, "kb_hit"),
        "samples": {
            "missing_source_chunks": [row for row in source_rows if row["status"] == "missing"][:12],
            "kp_not_in_word": [row for row in kp_rows if not row["word_hit"]][:20],
            "tasks_not_in_word": [row for row in task_rows if not row["word_hit"]][:20],
            "answers_not_in_word": [row for row in answer_rows if not row["word_hit"]][:20],
            "headings_not_in_kb": [row for row in heading_rows if not row["kb_hit"]][:20],
            "candidate_supplement_terms": candidate_terms[:40],
        },
        "source_rows": source_rows,
        "knowledge_point_rows": kp_rows,
        "operation_task_rows": task_rows,
        "answer_card_rows": answer_rows,
        "heading_rows": heading_rows,
    }


def build_kb_text(data: dict[str, Any]) -> str:
    tables = [
        "Chapter_Structure",
        "Knowledge_Points",
        "Answer_Cards",
        "Source_Chunks",
        "Operation_Tasks",
        "Operation_Steps",
        "Command_Cards",
        "Software_Objects",
        "Parameter_Settings",
        "Common_Errors",
        "Exercises",
        "Resources",
        "Synonyms_Questions",
        "RAG_Config",
    ]
    return "\n".join(
        json.dumps(row, ensure_ascii=False)
        for table in tables
        for row in data.get(table, [])
        if isinstance(row, dict)
    )


def audit_source_chunks(rows: object, compact_word_text: str) -> list[dict[str, Any]]:
    results = []
    if not isinstance(rows, list):
        return results
    for row in rows:
        if not isinstance(row, dict):
            continue
        excerpt = str(row.get("source_excerpt") or row.get("summary") or row.get("chunk_summary") or "")
        sample = compact(excerpt)
        status = "missing"
        support_terms: list[str] = []
        if "<w:" in excerpt or "</w:" in excerpt:
            status = "xml_residue"
        elif sample and sample in compact_word_text:
            status = "exact"
        elif fuzzy_excerpt_hit(sample, compact_word_text):
            status = "partial"
        else:
            support_terms = supported_terms(excerpt, compact_word_text)
            if len(support_terms) >= 2:
                status = "concept_supported"
        results.append(
            {
                "chunk_id": row.get("chunk_id"),
                "heading_path": row.get("heading_path"),
                "status": status,
                "support_terms": support_terms[:8],
                "excerpt_preview": excerpt[:120],
            }
        )
    return results


def fuzzy_excerpt_hit(sample: str, compact_word_text: str) -> bool:
    if len(sample) < 20:
        return False
    windows = [sample[:40], sample[-40:]]
    return any(len(window) >= 12 and window in compact_word_text for window in windows)


def audit_terms(rows: object, id_field: str, title_field: str, compact_word_text: str, kb_text: str) -> list[dict[str, Any]]:
    results = []
    if not isinstance(rows, list):
        return results
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get(title_field) or "").strip()
        aliases = collect_aliases(row)
        terms = [title, *aliases]
        hit_term = first_hit_term(terms, compact_word_text)
        results.append(
            {
                "id": row.get(id_field),
                "title": title,
                "word_hit": bool(hit_term),
                "matched_term": hit_term,
                "kb_hit_count": sum(1 for term in terms if term and term in kb_text),
            }
        )
    return results


def collect_aliases(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ["keywords", "aliases", "student_question_patterns", "software", "command_name"]:
        value = row.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif isinstance(value, str):
            values.extend(split_values(value))
    return [value for value in dedupe(values) if 2 <= len(value) <= 40]


def first_hit_term(terms: list[str], compact_text: str) -> str:
    for term in terms:
        if not term:
            continue
        compact_term = compact(term)
        if len(compact_term) >= 2 and compact_term in compact_text:
            return term
    return ""


def audit_answer_cards(rows: object, compact_word_text: str) -> list[dict[str, Any]]:
    results = []
    if not isinstance(rows, list):
        return results
    for row in rows:
        if not isinstance(row, dict):
            continue
        fields = [
            row.get("canonical_question"),
            row.get("source_excerpt"),
            row.get("concise_answer"),
            row.get("expanded_answer"),
        ]
        for key in ["answer_points", "operation_steps", "must_include", "must_check"]:
            value = row.get(key)
            if isinstance(value, list):
                fields.extend(value[:3])
            elif isinstance(value, str):
                fields.extend(split_values(value)[:3])
        terms = [str(item) for item in fields if item]
        hit_term = first_hit_term([term[:80] for term in terms], compact_word_text)
        results.append(
            {
                "answer_id": row.get("answer_id"),
                "canonical_question": row.get("canonical_question"),
                "word_hit": bool(hit_term),
                "matched_term": hit_term[:80] if hit_term else "",
            }
        )
    return results


def audit_headings(paragraphs: list[Paragraph], compact_kb_text: str) -> list[dict[str, Any]]:
    headings = []
    seen: set[str] = set()
    for para in paragraphs:
        text = para.text.strip()
        if not is_likely_heading(para, text):
            continue
        key = compact(text)
        if key in seen:
            continue
        seen.add(key)
        headings.append({"paragraph": para.index, "style": para.style, "heading": text, "kb_hit": key in compact_kb_text})
    return headings


def is_likely_heading(para: Paragraph, text: str) -> bool:
    if not text or len(text) > 80:
        return False
    if para.style in {"ab", "10", "TOC1", "TOC2", "TOC3"}:
        return True
    patterns = [
        r"^第[一二三四五六七八九十]+节",
        r"^[一二三四五六七八九十]+、",
        r"^\\([一二三四五六七八九十]+\\)",
        r"^\\d+\\.",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def extract_candidate_terms(word_text: str, kb_text: str) -> list[dict[str, Any]]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_+.#/-]{1,32}|[\\u4e00-\\u9fff]{2,12}", word_text)
    stop = {
        "道路工程",
        "设计",
        "模型",
        "进行",
        "通过",
        "可以",
        "用户",
        "系统",
        "数据",
        "方法",
        "平台",
        "功能",
        "工具",
        "操作",
        "图形",
        "命令",
        "var",
        "string",
        "new",
        "null",
        "static",
        "float",
        "byte",
        "while",
        "default",
    }
    counter = Counter(token for token in tokens if is_candidate_token(token, stop))
    rows = []
    compact_kb_text = compact(kb_text)
    for term, count in counter.most_common(160):
        if count < 2:
            continue
        if compact(term) in compact_kb_text:
            continue
        rows.append({"term": term, "word_count": count, "suggestion": "Word高频但知识库未直接命中，建议人工判断是否补充别名、知识点或任务问法"})
    return rows


def supported_terms(excerpt: str, compact_word_text: str) -> list[str]:
    terms = [term for term in significant_terms(excerpt) if compact(term) in compact_word_text]
    return dedupe(terms)


def significant_terms(text: str) -> list[str]:
    stop = {
        "通过",
        "可以",
        "进行",
        "用于",
        "支持",
        "完成",
        "建立",
        "设计",
        "操作",
        "任务",
        "步骤",
        "检查",
        "结果",
        "模型",
        "数据",
        "对象",
        "平台",
        "功能",
        "工具",
        "软件",
    }
    raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9_+.#/-]{2,32}|[\\u4e00-\\u9fff]{2,10}", text)
    return [term for term in raw_terms if is_candidate_token(term, stop)]


def is_candidate_token(token: str, stop: set[str]) -> bool:
    if not token or token in stop:
        return False
    if len(token) < 2 or len(token) > 36:
        return False
    if "<" in token or ">" in token or ":" in token:
        return False
    if token.isdigit():
        return False
    if re.fullmatch(r"\\d+[./-]\\d+(?:[./-]\\d+)?", token):
        return False
    if token.lower() in stop:
        return False
    return True


def write_chapter_reports(chapter_id: str, report: dict[str, Any]) -> None:
    out_dir = ROOT / "output" / f"{chapter_id}_rag_engine" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / f"{chapter_id}_word_extract.txt"
    alignment_json = out_dir / f"{chapter_id}_word_alignment.json"
    alignment_md = out_dir / f"{chapter_id}_word_alignment.md"

    extract_path.write_text(report.get("_word_text", ""), encoding="utf-8")
    alignment_json.write_text(json.dumps(public_report(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    alignment_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"{chapter_id}: {alignment_md}")


def public_report(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if not key.startswith("_")}


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['chapter_id']} Word教材对照核实与补充候选报告",
        "",
        f"章节：{report['title']}",
        f"Word段落范围：{report['word_range']['start_paragraph']} - {report['word_range']['end_paragraph']}，共 {report['word_range']['paragraphs']} 段，{report['word_characters']} 字符。",
        "",
        "## 数据概况",
        "",
        "| 表 | 数量 |",
        "|---|---:|",
    ]
    for key, value in report["kb_counts"].items():
        lines.append(f"| {key} | {value} |")

    lines.extend(["", "## 对照摘要", "", "| 项目 | 结果 |", "|---|---|"])
    lines.append(f"| Source_Chunks | {format_status_summary(report['source_chunk_alignment'])} |")
    lines.append(f"| Knowledge_Points | {format_bool_summary(report['knowledge_point_alignment'])} |")
    lines.append(f"| Operation_Tasks | {format_bool_summary(report['operation_task_alignment'])} |")
    lines.append(f"| Answer_Cards | {format_bool_summary(report['answer_card_alignment'])} |")
    lines.append(f"| Word标题覆盖 | {format_bool_summary(report['heading_coverage'])} |")

    sample_sections = [
        ("Source_Chunks未直接命中样例", "missing_source_chunks", "chunk_id", "excerpt_preview"),
        ("知识点标题/别名未直接命中Word样例", "kp_not_in_word", "id", "title"),
        ("操作任务未直接命中Word样例", "tasks_not_in_word", "id", "title"),
        ("答案卡未直接命中Word样例", "answers_not_in_word", "answer_id", "canonical_question"),
        ("Word标题未直接命中知识库样例", "headings_not_in_kb", "paragraph", "heading"),
        ("知识补充候选术语", "candidate_supplement_terms", "term", "suggestion"),
    ]
    for title, key, id_key, text_key in sample_sections:
        rows = report["samples"].get(key, [])
        lines.extend(["", f"## {title}", ""])
        if not rows:
            lines.append("- 无")
            continue
        for row in rows:
            label = row.get(id_key, "")
            text = str(row.get(text_key, ""))[:160].replace("\n", " ")
            extra = f"（Word出现 {row.get('word_count')} 次）" if row.get("word_count") else ""
            lines.append(f"- `{label}` {text}{extra}")

    lines.extend(
        [
            "",
            "## 使用说明",
            "",
            "- `exact` 表示知识库证据片段可在Word正文中直接规整命中；`partial` 表示首尾片段可命中，通常是摘要改写或标点差异；`missing` 需要人工复核。",
            "- 补充候选术语只作为人工审校入口，不自动写入知识库，避免把教材目录、页码或孤立高频词误当成知识点。",
            "",
        ]
    )
    return "\n".join(lines)


def compact_summary(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "chapter_id": report["chapter_id"],
            "word_range": report["word_range"],
            "source_chunks": report["source_chunk_alignment"],
            "knowledge_points": report["knowledge_point_alignment"],
            "operation_tasks": report["operation_task_alignment"],
            "answer_cards": report["answer_card_alignment"],
            "heading_coverage": report["heading_coverage"],
        }
        for report in reports
    ]


def summarize_status(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(row.get("status", "unknown") for row in rows)
    counter["total"] = len(rows)
    return dict(counter)


def summarize_bool(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    hit = sum(1 for row in rows if row.get(field))
    return {"hit": hit, "miss": len(rows) - hit, "total": len(rows)}


def format_status_summary(summary: dict[str, int]) -> str:
    return (
        f"exact {summary.get('exact', 0)} / partial {summary.get('partial', 0)} / "
        f"concept_supported {summary.get('concept_supported', 0)} / "
        f"xml_residue {summary.get('xml_residue', 0)} / missing {summary.get('missing', 0)} / "
        f"total {summary.get('total', 0)}"
    )


def format_bool_summary(summary: dict[str, int]) -> str:
    return f"命中 {summary.get('hit', 0)} / 未命中 {summary.get('miss', 0)} / total {summary.get('total', 0)}"


def split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value)
    return [item.strip() for item in re.split(r"[;；|,，\n]", text) if item.strip()]


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = compact(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def compact(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower()


if __name__ == "__main__":
    raise SystemExit(main())
