from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from audit_word_alignment_ch06_ch09 import extract_docx_paragraphs, locate_chapter_ranges
from review_ch10_ch11_source_boundaries import DEFAULT_DOCX


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVALS = ROOT / "data" / "review" / "ch10_ch11_p3_scene_source_boundary_manual_approvals.proposed.json"
FALLBACK_APPROVALS = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.draft.json"
DEFAULT_OUTPUT_JSON = ROOT / "output" / "ch11_p4_source_review_packet_2026-06-05.json"
DEFAULT_OUTPUT_MD = ROOT / "output" / "ch11_p4_source_review_packet_2026-06-05.md"
DEFAULT_OUTPUT_CSV = ROOT / "output" / "ch11_p4_source_review_packet_2026-06-05.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a focused P4 review packet for ch11 Source_Chunks.")
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--context", type=int, default=2)
    args = parser.parse_args()

    approvals_path = args.approvals if args.approvals.exists() else FALLBACK_APPROVALS
    approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
    paragraphs = extract_docx_paragraphs(args.docx)
    ranges = locate_chapter_ranges(paragraphs)
    ch11_start, ch11_end = ranges["ch11"]
    by_index = {para.index: para for para in paragraphs if ch11_start <= para.index < ch11_end}
    decisions = [
        item
        for item in approvals.get("decisions", [])
        if isinstance(item, dict)
        and item.get("chapter_id") == "ch11"
        and item.get("priority_group") == "P4_ch11_boundary_summary"
    ]

    items = [build_packet_item(item, by_index, args.context) for item in decisions]
    status_counts = Counter(str(item.get("review_status") or "") for item in items)
    suggestion_counts = Counter(str(item.get("suggested_decision") or "") for item in items)
    filled = sum(1 for item in items if item.get("current_decision"))
    payload = {
        "source_approvals": str(approvals_path),
        "source_docx": str(args.docx),
        "chapter_id": "ch11",
        "priority_group": "P4_ch11_boundary_summary",
        "purpose": (
            "Focused P4 review packet for ch11 boundary fragments and teaching summaries. "
            "Suggestions are not manual approvals."
        ),
        "items": items,
        "summary": {
            "total": len(items),
            "filled": filled,
            "open": len(items) - filled,
            "by_review_status": dict(sorted(status_counts.items())),
            "by_suggested_decision": dict(sorted(suggestion_counts.items())),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(args.csv, items)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "markdown": str(args.markdown),
                "csv": str(args.csv),
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def build_packet_item(item: dict[str, Any], by_index: dict[int, Any], context: int) -> dict[str, Any]:
    start = safe_int(item.get("approved_paragraph_start"))
    end = safe_int(item.get("approved_paragraph_end")) or start
    context_rows = []
    if start:
        for para_index in range(start - context, end + context + 1):
            para = by_index.get(para_index)
            if para is None:
                continue
            context_rows.append(
                {
                    "paragraph": para.index,
                    "role": "candidate" if start <= para.index <= end else "context",
                    "text": para.text,
                }
            )
    return {
        "chapter_id": item.get("chapter_id"),
        "chunk_id": item.get("chunk_id"),
        "priority_group": item.get("priority_group"),
        "review_status": item.get("review_status"),
        "suggested_decision": item.get("suggested_decision"),
        "current_decision": item.get("decision") or "",
        "source_excerpt_role": item.get("source_excerpt_role"),
        "source_excerpt": item.get("source_excerpt"),
        "candidate_score": item.get("candidate_score"),
        "score_margin": item.get("score_margin"),
        "candidate_span": {"start": start, "end": end},
        "candidate_text": item.get("candidate_text"),
        "candidate_reasons": item.get("candidate_reasons") or [],
        "matched_terms": item.get("matched_terms") or [],
        "context": context_rows,
        "review_prompt": review_prompt(item),
    }


def review_prompt(item: dict[str, Any]) -> str:
    status = str(item.get("review_status") or "")
    if status == "term_supported_summary_review":
        return (
            "核对术语锚点是否足以支撑教学摘要。若可支撑，使用 confirm_teaching_summary；"
            "若支撑不足，使用 manual_anchor_pending 或 reject_candidate。"
        )
    if status == "boundary_fragment_review":
        return (
            "核对候选段落是否为公式、列表或跨段边界片段。若边界可接受，使用 confirm_boundary_fragment；"
            "若需要拆分或补上下文，使用 split_required 或 manual_anchor_pending。"
        )
    return "核对 Source_Chunk 与候选 Word 段落的证据关系，并记录人工判断。"


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# ch11 P4 Source_Chunks 复核包",
        "",
        "说明：本报告用于辅助人工复核，不构成人工审批文件。建议项只代表自动分级结果，正式应用仍需人工确认。",
        "",
        f"- 总计：{summary['total']}",
        f"- 已填 decision：{summary['filled']}",
        f"- 未填 decision：{summary['open']}",
        f"- 按复核状态：{json.dumps(summary['by_review_status'], ensure_ascii=False)}",
        f"- 按建议决策：{json.dumps(summary['by_suggested_decision'], ensure_ascii=False)}",
        "",
    ]
    for item in payload["items"]:
        lines.extend(
            [
                f"## {item['chunk_id']} / {item['review_status']}",
                "",
                f"- 建议决策：`{item['suggested_decision']}`",
                f"- 当前 decision：`{item['current_decision'] or '(empty)'}`",
                f"- 候选段落：{item['candidate_span']['start']}-{item['candidate_span']['end']}",
                f"- score={item['candidate_score']} margin={item['score_margin']}",
                f"- 复核提示：{item['review_prompt']}",
                "",
                "Source_Chunk：",
                "",
                quote(item.get("source_excerpt") or ""),
                "",
                "候选及前后文：",
                "",
            ]
        )
        for row in item["context"]:
            marker = "候选" if row["role"] == "candidate" else "上下文"
            lines.append(f"**P{row['paragraph']} {marker}**")
            lines.append("")
            lines.append(quote(row["text"]))
            lines.append("")
    return "\n".join(lines)


def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "chapter_id",
                "chunk_id",
                "review_status",
                "suggested_decision",
                "current_decision",
                "candidate_start",
                "candidate_end",
                "candidate_score",
                "score_margin",
                "source_excerpt",
                "candidate_text",
                "review_prompt",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "chapter_id": item.get("chapter_id"),
                    "chunk_id": item.get("chunk_id"),
                    "review_status": item.get("review_status"),
                    "suggested_decision": item.get("suggested_decision"),
                    "current_decision": item.get("current_decision"),
                    "candidate_start": item.get("candidate_span", {}).get("start"),
                    "candidate_end": item.get("candidate_span", {}).get("end"),
                    "candidate_score": item.get("candidate_score"),
                    "score_margin": item.get("score_margin"),
                    "source_excerpt": item.get("source_excerpt"),
                    "candidate_text": item.get("candidate_text"),
                    "review_prompt": item.get("review_prompt"),
                }
            )


def quote(text: str) -> str:
    cleaned = str(text).strip()
    if not cleaned:
        return "> "
    return "\n".join("> " + line for line in cleaned.splitlines())


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
