from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from audit_word_alignment_ch06_ch09 import CHAPTERS, extract_docx_paragraphs, locate_chapter_ranges


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_CSV = ROOT / "output" / "ch10_ch11_word_manual_review_2026-06-05.csv"
DEFAULT_DOCX = (
    Path("F:/")
    / "编书"
    / "道路工程数字设计方法"
    / "05脚本及图片素材"
    / "批注版-道路工程数字设计方法-数字化教材稿.docx"
)
DEFAULT_OUTPUT_JSON = ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.json"
DEFAULT_OUTPUT_CSV = ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.csv"
DEFAULT_OUTPUT_MD = ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.md"

WATCH_CLASSES = {
    "summary_with_term_support",
    "cross_paragraph_or_formula_fragment",
    "needs_manual_textbook_anchor",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ch10/ch11 Source_Chunks evidence-boundary review packet.")
    parser.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW_CSV)
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    paragraphs = extract_docx_paragraphs(args.docx)
    chapter_ranges = locate_chapter_ranges(paragraphs)
    review_rows = load_review_rows(args.review_csv)
    packages = {chapter_id: load_raw_package(chapter_id) for chapter_id in ("ch10", "ch11")}

    results = []
    for item in review_rows:
        chapter_id = str(item.get("chapter_id") or "")
        chunk_id = str(item.get("object_id") or "")
        if chapter_id not in packages or not chunk_id:
            continue
        chunk = source_by_id(packages[chapter_id]).get(chunk_id)
        if not chunk:
            continue
        start, end = chapter_ranges[chapter_id]
        chapter_paragraphs = [para for para in paragraphs if start <= para.index < end]
        results.append(map_review_item(item, chunk, chapter_paragraphs))

    payload = {
        "source_review_csv": str(args.review_csv),
        "source_docx": str(args.docx),
        "chapters": build_chapter_payload(results),
        "summary": summarize(results),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_review_csv(args.output_csv, results)
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "output_csv": str(args.output_csv),
                "markdown": str(args.markdown),
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def load_review_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row.get("item_type") == "source_chunk" and row.get("classification") in WATCH_CLASSES
        ]


def load_raw_package(chapter_id: str) -> dict[str, Any]:
    path = next((ROOT / "data" / "raw" / chapter_id).glob("*.json"))
    return json.loads(path.read_text(encoding="utf-8-sig"))


def source_by_id(package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("chunk_id")): row
        for row in package.get("Source_Chunks", [])
        if isinstance(row, dict) and row.get("chunk_id")
    }


def map_review_item(item: dict[str, Any], chunk: dict[str, Any], paragraphs: list[Any]) -> dict[str, Any]:
    classification = str(item.get("classification") or "")
    query = build_query(chunk, item)
    candidates = []
    for index in range(len(paragraphs)):
        for window_size in (1, 2, 3):
            window = paragraphs[index : index + window_size]
            if not window:
                continue
            text = " ".join(para.text for para in window)
            score, reasons, terms = score_candidate(query, text)
            if score <= 0:
                continue
            candidates.append(
                {
                    "paragraph_start": window[0].index,
                    "paragraph_end": window[-1].index,
                    "score": round(score, 6),
                    "reasons": reasons,
                    "matched_terms": terms[:10],
                    "text": text,
                }
            )
    candidates.sort(key=lambda row: float(row.get("score") or 0), reverse=True)
    top = dedupe_candidates(candidates)[:5]
    best = top[0] if top else empty_candidate()
    second_score = float(top[1].get("score") or 0) if len(top) > 1 else 0.0
    review_status, action = classify_review_status(classification, best, second_score)
    return {
        "chapter_id": item.get("chapter_id"),
        "chunk_id": chunk.get("chunk_id"),
        "section_id": chunk.get("section_id"),
        "heading_path": chunk.get("heading_path") or item.get("title_or_heading"),
        "original_classification": classification,
        "review_status": review_status,
        "recommended_action": action,
        "source_excerpt_role": source_excerpt_role(review_status),
        "source_excerpt": chunk.get("source_excerpt") or item.get("excerpt_preview") or "",
        "chunk_summary": chunk.get("chunk_summary") or chunk.get("summary") or "",
        "best_score": best.get("score") or 0,
        "score_margin": round(float(best.get("score") or 0) - second_score, 6),
        "top_candidates": top,
    }


def build_query(chunk: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    excerpt = str(chunk.get("source_excerpt") or item.get("excerpt_preview") or "")
    summary = str(chunk.get("chunk_summary") or chunk.get("summary") or "")
    heading = str(chunk.get("heading_path") or item.get("title_or_heading") or "")
    keywords = to_list(chunk.get("keywords"))
    terms = extract_terms([excerpt, summary, heading, *keywords])
    return {"excerpt": excerpt, "summary": summary, "heading": heading, "terms": terms}


def score_candidate(query: dict[str, Any], text: str) -> tuple[float, list[str], list[str]]:
    text_norm = normalize(text)
    if not text_norm:
        return 0.0, [], []
    excerpt_score = text_similarity(query["excerpt"], text)
    summary_score = text_similarity(query["summary"], text)
    heading_score = text_similarity(query["heading"].split(">")[-1], text)
    matched_terms = [term for term in query["terms"] if normalize(term) and normalize(term) in text_norm]
    term_score = len(matched_terms) / len(query["terms"]) if query["terms"] else 0.0
    score = 0.48 * excerpt_score + 0.24 * summary_score + 0.10 * heading_score + 0.18 * term_score
    if excerpt_score >= 0.65:
        score += 0.10
    elif summary_score >= 0.65:
        score += 0.06
    if len(matched_terms) >= 3:
        score += 0.04
    score = min(1.0, score)

    reasons = []
    if excerpt_score >= 0.18:
        reasons.append(f"excerpt:{excerpt_score:.2f}")
    if summary_score >= 0.18:
        reasons.append(f"summary:{summary_score:.2f}")
    if heading_score >= 0.18:
        reasons.append(f"heading:{heading_score:.2f}")
    if matched_terms:
        reasons.append("terms:" + ",".join(matched_terms[:8]))
    return score, reasons, matched_terms


def classify_review_status(classification: str, best: dict[str, Any], second_score: float) -> tuple[str, str]:
    score = float(best.get("score") or 0)
    margin = score - second_score
    if classification == "summary_with_term_support":
        return (
            "term_supported_summary_review",
            "保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。",
        )
    if classification == "cross_paragraph_or_formula_fragment":
        return (
            "boundary_fragment_review",
            "疑似跨段、公式或列表边界片段；人工确认是否拆分、补公式上下文或仅保留为摘要。",
        )
    if score >= 0.46 and margin >= 0.025:
        return (
            "candidate_anchor_review",
            "已生成候选 Word 段落；人工确认后可作为概念依据对应，不标记为逐字原文。",
        )
    return (
        "manual_anchor_required",
        "未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。",
    )


def source_excerpt_role(review_status: str) -> str:
    mapping = {
        "term_supported_summary_review": "teaching_summary_with_term_support_not_verbatim",
        "boundary_fragment_review": "boundary_fragment_needs_manual_confirmation",
        "candidate_anchor_review": "candidate_concept_anchor_not_verbatim",
        "manual_anchor_required": "manual_textbook_anchor_required",
    }
    return mapping.get(review_status, "needs_evidence_boundary_review")


def dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    seen: set[tuple[int, int]] = set()
    for candidate in candidates:
        key = (int(candidate.get("paragraph_start") or 0), int(candidate.get("paragraph_end") or 0))
        if key in seen:
            continue
        seen.add(key)
        results.append(candidate)
    return results


def empty_candidate() -> dict[str, Any]:
    return {
        "paragraph_start": None,
        "paragraph_end": None,
        "score": 0,
        "reasons": [],
        "matched_terms": [],
        "text": "",
    }


def text_similarity(left: str, right: str) -> float:
    left_norm = normalize(left)
    right_norm = normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm in right_norm:
        return 1.0
    if right_norm in left_norm:
        return len(right_norm) / len(left_norm)
    sequence = SequenceMatcher(None, left_norm, right_norm).ratio()
    left_grams = ngrams(left_norm, 3)
    right_grams = ngrams(right_norm, 3)
    jaccard = len(left_grams & right_grams) / len(left_grams | right_grams) if left_grams | right_grams else 0.0
    return 0.45 * sequence + 0.55 * jaccard


def ngrams(text: str, size: int) -> set[str]:
    if len(text) <= size:
        return {text} if text else set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def extract_terms(values: list[str]) -> list[str]:
    generic = {"道路", "工程", "设计", "方法", "系统", "模型", "数据", "应用", "数字", "智能", "章节"}
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        for raw in re.findall(r"[A-Za-z][A-Za-z0-9_+.#/-]{1,32}|[\u4e00-\u9fff]{2,12}", str(value)):
            term = raw.strip()
            key = normalize(term)
            if not key or term in generic or len(key) < 2 or key in seen:
                continue
            seen.add(key)
            terms.append(term)
            if len(terms) >= 20:
                return terms
    return terms


def normalize(text: str) -> str:
    return re.sub(r"\s+|[，。；：、,.!?！？（）()《》“”\"'\\-—_/]", "", str(text)).lower()


def to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[;；,，\n]", str(value)) if item.strip()]


def build_chapter_payload(results: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for chapter_id in ("ch10", "ch11"):
        chapter_results = [row for row in results if row.get("chapter_id") == chapter_id]
        payload[chapter_id] = {
            "summary": summarize(chapter_results),
            "source_boundary_reviews": chapter_results,
        }
    return payload


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(results),
        "by_review_status": dict(sorted(Counter(str(row.get("review_status") or "") for row in results).items())),
        "by_original_classification": dict(sorted(Counter(str(row.get("original_classification") or "") for row in results).items())),
    }


def write_review_csv(path: Path, results: list[dict[str, Any]]) -> None:
    fields = [
        "chapter_id",
        "chunk_id",
        "original_classification",
        "review_status",
        "best_score",
        "score_margin",
        "paragraph_start",
        "paragraph_end",
        "recommended_action",
        "source_excerpt_role",
        "candidate_preview",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            best = row["top_candidates"][0] if row.get("top_candidates") else empty_candidate()
            writer.writerow(
                {
                    "chapter_id": row.get("chapter_id"),
                    "chunk_id": row.get("chunk_id"),
                    "original_classification": row.get("original_classification"),
                    "review_status": row.get("review_status"),
                    "best_score": row.get("best_score"),
                    "score_margin": row.get("score_margin"),
                    "paragraph_start": best.get("paragraph_start"),
                    "paragraph_end": best.get("paragraph_end"),
                    "recommended_action": row.get("recommended_action"),
                    "source_excerpt_role": row.get("source_excerpt_role"),
                    "candidate_preview": compact_preview(best.get("text") or "", 160),
                }
            )


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 第10、11章 Source_Chunks 证据边界复核包",
        "",
        "说明：本报告只生成候选教材段落和复核动作，不把候选结果标记为人工确认，也不把教学摘要伪装成逐字原文。",
        "",
        "## 总览",
        "",
        f"- 总计：{payload['summary']['total']}",
        f"- 按复核状态：`{payload['summary']['by_review_status']}`",
        f"- 按原始分级：`{payload['summary']['by_original_classification']}`",
        "",
    ]
    for chapter_id, chapter in payload["chapters"].items():
        lines.extend([f"## {chapter_id}", "", f"- 统计：`{chapter['summary']}`", "", "| Chunk | 原分级 | 复核状态 | 候选段 | 分数 | 动作 |", "|---|---|---|---:|---:|---|"])
        for row in chapter["source_boundary_reviews"]:
            best = row["top_candidates"][0] if row.get("top_candidates") else empty_candidate()
            lines.append(
                f"| `{row['chunk_id']}` | {row['original_classification']} | {row['review_status']} | "
                f"{best.get('paragraph_start') or ''}-{best.get('paragraph_end') or ''} | "
                f"{float(row.get('best_score') or 0):.3f} | {row['recommended_action']} |"
            )
        lines.append("")
    return "\n".join(lines)


def compact_preview(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(text)).strip()
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"


if __name__ == "__main__":
    raise SystemExit(main())
