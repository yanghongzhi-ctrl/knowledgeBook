from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOUNDARY_REVIEW = ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.json"
DEFAULT_TEMPLATE = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.template.json"
DEFAULT_PRIORITY_CSV = ROOT / "output" / "ch10_ch11_source_boundary_review_priority_2026-06-05.csv"
DEFAULT_DOSSIER = ROOT / "output" / "ch10_ch11_source_boundary_review_dossier_2026-06-05.md"
DEFAULT_WEB_DATA = ROOT / "web" / "source-review-data.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build manual approval template for ch10/ch11 Source_Chunks boundary review.")
    parser.add_argument("--boundary-review", type=Path, default=DEFAULT_BOUNDARY_REVIEW)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--priority-csv", type=Path, default=DEFAULT_PRIORITY_CSV)
    parser.add_argument("--dossier", type=Path, default=DEFAULT_DOSSIER)
    parser.add_argument("--web-data", type=Path, default=DEFAULT_WEB_DATA)
    args = parser.parse_args()

    review = json.loads(args.boundary_review.read_text(encoding="utf-8"))
    rows = collect_rows(review)
    decisions = [approval_item(row) for row in rows]
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_boundary_review": str(args.boundary_review),
        "instructions": [
            "Copy this file to ch10_ch11_source_boundary_manual_approvals.json before editing decisions.",
            "Leave decision empty to keep a Source_Chunk in needs_evidence_boundary_review.",
            "Allowed decisions: confirm_candidate_anchor, confirm_teaching_summary, confirm_boundary_fragment, split_required, reject_candidate, manual_anchor_pending.",
            "A confirmed candidate anchor means concept correspondence only, not a verbatim textbook quote.",
        ],
        "decisions": decisions,
    }

    args.template.parent.mkdir(parents=True, exist_ok=True)
    args.template.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_priority_csv(args.priority_csv, decisions)
    args.dossier.write_text(render_dossier(review, decisions), encoding="utf-8")
    args.web_data.write_text(json.dumps(web_payload(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "template": str(args.template),
                "priority_csv": str(args.priority_csv),
                "dossier": str(args.dossier),
                "web_data": str(args.web_data),
                "items": len(decisions),
                "by_priority": count_by(decisions, "priority_group"),
                "by_suggested_decision": count_by(decisions, "suggested_decision"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def collect_rows(review: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chapter_id in ("ch10", "ch11"):
        chapter = (review.get("chapters") or {}).get(chapter_id) or {}
        for row in chapter.get("source_boundary_reviews") or []:
            if isinstance(row, dict):
                rows.append(row)
    rows.sort(key=sort_key)
    return rows


def sort_key(row: dict[str, Any]) -> tuple[int, str]:
    chapter = str(row.get("chapter_id") or "")
    status = str(row.get("review_status") or "")
    order = {
        ("ch10", "candidate_anchor_review"): 1,
        ("ch10", "manual_anchor_required"): 2,
        ("ch10", "boundary_fragment_review"): 3,
        ("ch10", "term_supported_summary_review"): 4,
        ("ch11", "candidate_anchor_review"): 5,
        ("ch11", "manual_anchor_required"): 6,
        ("ch11", "boundary_fragment_review"): 7,
        ("ch11", "term_supported_summary_review"): 8,
    }
    return (order.get((chapter, status), 99), str(row.get("chunk_id") or ""))


def approval_item(row: dict[str, Any]) -> dict[str, Any]:
    best = (row.get("top_candidates") or [{}])[0]
    status = str(row.get("review_status") or "")
    suggested = suggested_decision(status)
    return {
        "chapter_id": row.get("chapter_id"),
        "chunk_id": row.get("chunk_id"),
        "priority_group": priority_group(row),
        "review_status": status,
        "suggested_decision": suggested,
        "decision": "",
        "approved_paragraph_start": best.get("paragraph_start"),
        "approved_paragraph_end": best.get("paragraph_end"),
        "candidate_score": row.get("best_score"),
        "score_margin": row.get("score_margin"),
        "source_excerpt_role": row.get("source_excerpt_role"),
        "source_excerpt": row.get("source_excerpt"),
        "candidate_text": best.get("text") or "",
        "candidate_reasons": best.get("reasons") or [],
        "matched_terms": best.get("matched_terms") or [],
        "reviewer_notes": "",
    }


def suggested_decision(status: str) -> str:
    return {
        "candidate_anchor_review": "confirm_candidate_anchor",
        "term_supported_summary_review": "confirm_teaching_summary",
        "boundary_fragment_review": "confirm_boundary_fragment",
        "manual_anchor_required": "manual_anchor_pending",
    }.get(status, "manual_anchor_pending")


def priority_group(row: dict[str, Any]) -> str:
    chapter = str(row.get("chapter_id") or "")
    status = str(row.get("review_status") or "")
    if chapter == "ch10" and status == "candidate_anchor_review":
        return "P1_ch10_quick_confirm"
    if chapter == "ch10" and status == "manual_anchor_required":
        return "P1_ch10_formula_gap"
    if chapter == "ch10":
        return "P2_ch10_boundary_summary"
    if chapter == "ch11" and status == "candidate_anchor_review":
        return "P2_ch11_quick_confirm"
    if chapter == "ch11" and status == "manual_anchor_required":
        return "P3_ch11_application_scene_manual"
    return "P4_ch11_boundary_summary"


def write_priority_csv(path: Path, decisions: list[dict[str, Any]]) -> None:
    fields = [
        "priority_group",
        "chapter_id",
        "chunk_id",
        "review_status",
        "suggested_decision",
        "decision",
        "approved_paragraph_start",
        "approved_paragraph_end",
        "candidate_score",
        "score_margin",
        "source_excerpt_role",
        "source_excerpt",
        "candidate_text",
        "reviewer_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in decisions:
            writer.writerow({field: row.get(field) for field in fields})


def render_dossier(review: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    lines = [
        "# 第10、11章 Source_Chunks 人工复核 Dossier",
        "",
        "说明：本文件按优先级展示 source_excerpt、候选 Word 段落和建议动作。候选段落仅用于人工复核，不表示已确认逐字引用。",
        "",
        "## 总览",
        "",
        f"- 总计：{len(decisions)}",
        f"- 原复核包统计：`{review.get('summary')}`",
        f"- 优先级分布：`{count_by(decisions, 'priority_group')}`",
        "",
    ]
    current_group = ""
    for item in decisions:
        group = str(item.get("priority_group") or "")
        if group != current_group:
            current_group = group
            lines.extend(["", f"## {group}", ""])
        lines.extend(
            [
                f"### {item.get('chapter_id')} / {item.get('chunk_id')}",
                "",
                f"- 复核状态：`{item.get('review_status')}`",
                f"- 建议决策：`{item.get('suggested_decision')}`",
                f"- 候选段落：{item.get('approved_paragraph_start')}-{item.get('approved_paragraph_end')}，score={item.get('candidate_score')}",
                f"- 匹配依据：`{item.get('candidate_reasons')}`",
                "",
                "Source_Chunk：",
                "",
                blockquote(item.get("source_excerpt") or ""),
                "",
                "候选 Word 段落：",
                "",
                blockquote(item.get("candidate_text") or ""),
                "",
            ]
        )
    return "\n".join(lines)


def web_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": payload.get("generated_at"),
        "instructions": payload.get("instructions") or [],
        "summary": {
            "items": len(payload.get("decisions") or []),
            "by_priority": count_by(payload.get("decisions") or [], "priority_group"),
            "by_suggested_decision": count_by(payload.get("decisions") or [], "suggested_decision"),
        },
        "decisions": payload.get("decisions") or [],
    }


def blockquote(text: str) -> str:
    cleaned = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return "> "
    return "\n".join("> " + line for line in cleaned.splitlines())


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
