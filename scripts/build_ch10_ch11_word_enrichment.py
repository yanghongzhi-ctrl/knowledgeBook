from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALIGNMENT = ROOT / "output" / "word_alignment_ch10_ch11_2026-06-04.json"
DEFAULT_OUTPUT = ROOT / "output" / "ch10_ch11_word_enrichment_2026-06-05.json"
DEFAULT_MARKDOWN = ROOT / "output" / "ch10_ch11_word_enrichment_2026-06-05.md"
DEFAULT_REVIEW_JSON = ROOT / "output" / "ch10_ch11_word_manual_review_2026-06-05.json"
DEFAULT_REVIEW_CSV = ROOT / "output" / "ch10_ch11_word_manual_review_2026-06-05.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Word alignment enrichment plan for chapter 10 and 11.")
    parser.add_argument("--alignment", type=Path, default=DEFAULT_ALIGNMENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--review-json", type=Path, default=DEFAULT_REVIEW_JSON)
    parser.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW_CSV)
    args = parser.parse_args()

    alignment = json.loads(args.alignment.read_text(encoding="utf-8"))
    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_alignment": str(args.alignment),
        "chapters": {},
    }

    for report in alignment.get("chapters", []):
        chapter_id = str(report.get("chapter_id") or "")
        if chapter_id not in {"ch10", "ch11"}:
            continue
        package = load_raw_package(chapter_id)
        result["chapters"][chapter_id] = build_chapter_enrichment(chapter_id, report, package)

    result["summary"] = build_summary(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(result), encoding="utf-8")
    review_rows = build_manual_review_rows(result)
    args.review_json.write_text(json.dumps(review_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_manual_review_csv(args.review_csv, review_rows)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "markdown": str(args.markdown),
                "review_json": str(args.review_json),
                "review_csv": str(args.review_csv),
                "review_rows": len(review_rows),
                "summary": result["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def load_raw_package(chapter_id: str) -> dict[str, Any]:
    raw_dir = ROOT / "data/raw" / chapter_id
    path = next(raw_dir.glob("*知识库*.json"))
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_chapter_enrichment(chapter_id: str, report: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    kp_by_id = {str(row.get("kp_id")): row for row in package.get("Knowledge_Points", []) if isinstance(row, dict)}
    card_by_id = {str(row.get("answer_id")): row for row in package.get("Answer_Cards", []) if isinstance(row, dict)}
    source_status = {str(row.get("chunk_id")): row for row in report.get("source_rows", []) if isinstance(row, dict)}
    kp_hits = {str(row.get("id")): bool(row.get("word_hit")) for row in report.get("knowledge_point_rows", []) if isinstance(row, dict)}

    answer_classifications = [
        classify_answer_card(row, card_by_id, kp_by_id, source_status, kp_hits)
        for row in report.get("answer_card_rows", [])
        if isinstance(row, dict) and not row.get("word_hit")
    ]
    heading_mappings = [
        map_heading(row, package)
        for row in report.get("heading_rows", [])
        if isinstance(row, dict) and not row.get("kb_hit")
    ]
    source_classifications = [
        classify_source_chunk(row)
        for row in report.get("source_rows", [])
        if isinstance(row, dict)
    ]

    return {
        "answer_card_classifications": answer_classifications,
        "heading_mappings": heading_mappings,
        "source_chunk_classifications": source_classifications,
        "apply": {
            "answer_card_support": answer_classifications,
            "heading_aliases": [row for row in heading_mappings if row.get("auto_apply")],
            "source_chunk_notes": source_classifications,
        },
        "summary": {
            "answers_by_classification": count_by(answer_classifications, "classification"),
            "headings_auto_apply": sum(1 for row in heading_mappings if row.get("auto_apply")),
            "headings_manual_review": sum(1 for row in heading_mappings if not row.get("auto_apply")),
            "source_by_classification": count_by(source_classifications, "classification"),
        },
    }


def classify_answer_card(
    audit_row: dict[str, Any],
    card_by_id: dict[str, dict[str, Any]],
    kp_by_id: dict[str, dict[str, Any]],
    source_status: dict[str, dict[str, Any]],
    kp_hits: dict[str, bool],
) -> dict[str, Any]:
    answer_id = str(audit_row.get("answer_id") or "")
    card = card_by_id.get(answer_id, {})
    related_kps = split_values(card.get("related_kps"))
    evidence_chunks = split_values(card.get("evidence_chunks"))
    related_kp_hit = any(kp_hits.get(kp_id) for kp_id in related_kps)
    evidence_states = [source_status.get(chunk_id, {}).get("status", "unknown") for chunk_id in evidence_chunks]
    question = str(card.get("canonical_question") or audit_row.get("canonical_question") or "")
    qtype = str(card.get("question_type") or "")

    if related_kp_hit and any(state in {"exact", "partial", "concept_supported"} for state in evidence_states):
        if qtype in {"why", "application", "comparison", "summary", "review"} or has_teaching_question_word(question):
            classification = "teaching_rewrite_supported"
            action = "保留答案卡，标记为教学化改写；不强制伪造为教材原句。"
        else:
            classification = "needs_question_alias"
            action = "补充问法别名或标题触发词，使教材标题与学生问法更容易命中。"
    elif related_kp_hit:
        classification = "needs_question_alias"
        action = "相关知识点已在Word命中，优先补充别名和检索关键词。"
    else:
        classification = "needs_textbook_anchor"
        action = "需要人工确认教材锚点或收窄答案边界。"

    return {
        "answer_id": answer_id,
        "canonical_question": question,
        "classification": classification,
        "recommended_action": action,
        "related_kps": related_kps,
        "related_kp_hit": related_kp_hit,
        "evidence_chunks": evidence_chunks,
        "evidence_statuses": evidence_states,
    }


def has_teaching_question_word(question: str) -> bool:
    return any(word in question for word in ["为什么", "如何", "作用", "区别", "适合", "体现", "注意", "复习", "应用"])


def map_heading(audit_row: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    heading = str(audit_row.get("heading") or "")
    candidates: list[dict[str, Any]] = []
    for row in package.get("Chapter_Structure", []):
        if isinstance(row, dict):
            candidates.append(
                score_candidate(
                    heading,
                    "chapter_structure",
                    str(row.get("node_id") or row.get("section_id") or row.get("title") or ""),
                    candidate_text(row, ["title", "aliases", "keywords", "knowledge_focus", "summary", "description"]),
                )
            )
    for row in package.get("Knowledge_Points", []):
        if isinstance(row, dict):
            candidates.append(score_candidate(heading, "knowledge_point", str(row.get("kp_id") or ""), candidate_text(row, ["title", "aliases", "keywords", "definition"])))
    for row in package.get("Answer_Cards", []):
        if isinstance(row, dict):
            candidates.append(score_candidate(heading, "answer_card", str(row.get("answer_id") or ""), candidate_text(row, ["canonical_question", "student_question_patterns", "answer_points"])))
    for row in package.get("Resources", []):
        if isinstance(row, dict):
            candidates.append(score_candidate(heading, "resource", str(row.get("resource_id") or ""), candidate_text(row, ["title", "reference_aliases", "description"])))
    candidates = sorted((row for row in candidates if row["score"] > 0), key=lambda row: row["score"], reverse=True)
    best = candidates[0] if candidates else {"target_type": "", "target_id": "", "score": 0.0, "matched_terms": []}
    auto_apply = best["score"] >= 0.42
    return {
        "paragraph": audit_row.get("paragraph"),
        "heading": heading,
        "target_type": best.get("target_type"),
        "target_id": best.get("target_id"),
        "score": best.get("score"),
        "matched_terms": best.get("matched_terms", []),
        "auto_apply": auto_apply,
        "recommended_action": "自动补充为标题别名/检索关键词。" if auto_apply else "保留人工复核，避免错误绑定标题。",
        "candidate_targets": candidates[:5],
    }


def classify_source_chunk(audit_row: dict[str, Any]) -> dict[str, Any]:
    status = str(audit_row.get("status") or "")
    preview = str(audit_row.get("excerpt_preview") or "")
    support_terms = split_values(audit_row.get("support_terms"))
    if status == "exact":
        classification = "direct_textbook_evidence"
        note = "证据片段可在Word正文中直接规整命中。"
    elif status == "partial":
        classification = "partial_or_boundary_variation"
        note = "证据片段首尾或局部可命中，通常为标点、截断或跨句边界差异。"
    elif status == "concept_supported":
        classification = "concept_supported_summary"
        note = "片段不是教材原句，但关键概念在Word中可支撑。"
    elif support_terms:
        classification = "summary_with_term_support"
        note = "片段主体未直接命中，但存在可追溯术语支撑。"
    elif looks_cross_paragraph(preview):
        classification = "cross_paragraph_or_formula_fragment"
        note = "疑似跨段、公式、编号或图表边界片段，建议人工确认证据边界。"
    else:
        classification = "needs_manual_textbook_anchor"
        note = "未发现直接文本或术语支撑，需要人工确认教材锚点或修订摘要边界。"
    return {
        "chunk_id": audit_row.get("chunk_id"),
        "heading_path": audit_row.get("heading_path"),
        "word_status": status,
        "classification": classification,
        "support_terms": support_terms,
        "excerpt_preview": preview[:240],
        "evidence_boundary_note": note,
    }


def looks_cross_paragraph(text: str) -> bool:
    return bool(re.search(r"（\\d+）|\\(\\d+\\)|^\\d+\\.|如下|公式|目标|解支配|折扣回报|图\\d+", text))


def score_candidate(heading: str, target_type: str, target_id: str, text: str) -> dict[str, Any]:
    heading_options = heading_variants(heading)
    heading_norm = compact(heading)
    text_norm = compact(text)
    heading_keys = {compact(option) for option in heading_options}
    heading_keys.update(semantic_compact(option) for option in heading_options)
    heading_keys = {key for key in heading_keys if key}
    text_keys = {text_norm, semantic_compact(text)}
    text_keys = {key for key in text_keys if key}
    heading_terms = set()
    for option in heading_options:
        heading_terms.update(tokens(option))
    text_terms = set(tokens(text))
    overlap = heading_terms & text_terms
    score = 0.0
    if any(heading_key in text_key for heading_key in heading_keys for text_key in text_keys):
        score += 1.0
    if any(text_key in heading_key and len(text_key) >= 4 for heading_key in heading_keys for text_key in text_keys):
        score += 0.7
    bigram_ratio = max((chinese_bigram_ratio(heading_key, text_key) for heading_key in heading_keys for text_key in text_keys), default=0.0)
    if bigram_ratio >= 0.7:
        score += min(0.6, bigram_ratio * 0.6)
    if heading_terms:
        score += len(overlap) / max(1, len(heading_terms))
    if overlap:
        score += min(0.25, len(overlap) * 0.04)
    return {
        "target_type": target_type,
        "target_id": target_id,
        "score": round(score, 4),
        "matched_terms": sorted(overlap),
    }


def heading_variants(text: str) -> list[str]:
    variants = [text]
    stripped = re.sub(r"^\s*第[一二三四五六七八九十百千0-9]+[章节]\s*", "", text)
    stripped = re.sub(r"^\s*[一二三四五六七八九十]+[、.．]\s*", "", stripped)
    stripped = re.sub(r"^\s*[（(][一二三四五六七八九十0-9]+[）)]\s*", "", stripped)
    stripped = re.sub(r"^\s*\d+[、.．]\s*", "", stripped)
    if stripped and stripped != text:
        variants.append(stripped)
    return unique_list(variants)


def candidate_text(row: dict[str, Any], fields: list[str]) -> str:
    values: list[str] = []
    for field in fields:
        value = row.get(field)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif value:
            values.append(str(value))
    return "\n".join(values)


def tokens(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_+.#/-]{1,32}|[\u4e00-\u9fff]{2,12}", text)
    stop = {"道路", "设计", "方法", "系统", "模型", "数据", "技术", "应用", "工程", "智能", "数字", "孪生"}
    return [item for item in raw if item not in stop and len(item) >= 2]


def compact(text: str) -> str:
    return re.sub(r"\s+|[，。；：、,.!?！？（）()《》“”\"'\\-—_]", "", text).lower()


def semantic_compact(text: str) -> str:
    key = compact(text)
    for noise in ["的", "流程", "示意", "图"]:
        key = key.replace(noise, "")
    return key


def chinese_bigram_ratio(a: str, b: str) -> float:
    if len(a) < 4 or len(b) < 4:
        return 0.0
    a_bigrams = {a[index : index + 2] for index in range(len(a) - 1)}
    b_bigrams = {b[index : index + 2] for index in range(len(b) - 1)}
    if not a_bigrams:
        return 0.0
    return len(a_bigrams & b_bigrams) / len(a_bigrams)


def split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[;；,，\n]", str(value)) if item.strip()]


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter = Counter(str(row.get(key) or "") for row in rows)
    return dict(sorted(counter.items()))


def build_manual_review_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    watch_source_classes = {
        "summary_with_term_support",
        "cross_paragraph_or_formula_fragment",
        "needs_manual_textbook_anchor",
    }
    for chapter_id, chapter in result.get("chapters", {}).items():
        for item in chapter.get("heading_mappings", []):
            if not isinstance(item, dict) or item.get("auto_apply"):
                continue
            rows.append(
                {
                    "chapter_id": chapter_id,
                    "item_type": "heading",
                    "object_id": "",
                    "title_or_heading": item.get("heading") or "",
                    "classification": "heading_needs_manual_mapping",
                    "recommended_action": item.get("recommended_action") or "",
                    "target_type": item.get("target_type") or "",
                    "target_id": item.get("target_id") or "",
                    "score": item.get("score") or 0,
                    "excerpt_preview": "",
                    "reviewer_decision": "",
                    "reviewer_notes": "",
                }
            )
        for item in chapter.get("source_chunk_classifications", []):
            if not isinstance(item, dict) or item.get("classification") not in watch_source_classes:
                continue
            rows.append(
                {
                    "chapter_id": chapter_id,
                    "item_type": "source_chunk",
                    "object_id": item.get("chunk_id") or "",
                    "title_or_heading": item.get("heading_path") or "",
                    "classification": item.get("classification") or "",
                    "recommended_action": item.get("evidence_boundary_note") or "",
                    "target_type": "",
                    "target_id": "",
                    "score": "",
                    "excerpt_preview": item.get("excerpt_preview") or "",
                    "reviewer_decision": "",
                    "reviewer_notes": "",
                }
            )
    return rows


def write_manual_review_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "chapter_id",
        "item_type",
        "object_id",
        "title_or_heading",
        "classification",
        "recommended_action",
        "target_type",
        "target_id",
        "score",
        "excerpt_preview",
        "reviewer_decision",
        "reviewer_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def unique_list(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results


def build_summary(result: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for chapter_id, chapter in result["chapters"].items():
        summary[chapter_id] = chapter["summary"]
    return summary


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 第10、11章 Word 补强候选报告",
        "",
        f"生成时间：{result['generated_at']}",
        "",
    ]
    for chapter_id, chapter in result["chapters"].items():
        lines.extend([f"## {chapter_id}", "", "### 汇总", ""])
        lines.append("| 项目 | 结果 |")
        lines.append("|---|---|")
        lines.append(f"| 答案卡分级 | {chapter['summary']['answers_by_classification']} |")
        lines.append(f"| 标题自动补强 | {chapter['summary']['headings_auto_apply']} |")
        lines.append(f"| 标题人工复核 | {chapter['summary']['headings_manual_review']} |")
        lines.append(f"| Source_Chunks分级 | {chapter['summary']['source_by_classification']} |")
        lines.extend(["", "### 自动标题补强候选", ""])
        for row in chapter["apply"]["heading_aliases"][:30]:
            lines.append(f"- `{row['heading']}` -> `{row['target_type']}:{row['target_id']}` score={row['score']}")
        lines.extend(["", "### 答案卡未直接命中分级样例", ""])
        for row in chapter["answer_card_classifications"][:30]:
            lines.append(f"- `{row['answer_id']}` {row['classification']}：{row['canonical_question']}")
        lines.extend(["", "### Source_Chunks需人工关注样例", ""])
        watch = [row for row in chapter["source_chunk_classifications"] if row["classification"] in {"summary_with_term_support", "cross_paragraph_or_formula_fragment", "needs_manual_textbook_anchor"}]
        for row in watch[:30]:
            lines.append(f"- `{row['chunk_id']}` {row['classification']}：{row['evidence_boundary_note']}")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
