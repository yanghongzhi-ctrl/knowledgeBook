from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVALS = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.draft.json"
DEFAULT_P2_PACKET = ROOT / "output" / "ch10_p2_source_review_packet_2026-06-05.json"
DEFAULT_OUTPUT = ROOT / "data" / "review" / "ch10_p2_source_boundary_manual_approvals.proposed.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a non-active proposed approval file for ch10 P2 Source_Chunks.")
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--p2-packet", type=Path, default=DEFAULT_P2_PACKET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    approvals = json.loads(args.approvals.read_text(encoding="utf-8"))
    packet = json.loads(args.p2_packet.read_text(encoding="utf-8"))
    suggestions = {str(item.get("chunk_id") or ""): item for item in packet.get("items", [])}
    decisions = []
    changed_chunk_ids: list[str] = []
    for item in approvals.get("decisions", []):
        if not isinstance(item, dict):
            continue
        row = dict(item)
        suggestion = suggestions.get(str(row.get("chunk_id") or ""))
        if suggestion and not str(row.get("decision") or "").strip():
            row.update(proposed_fields(row, suggestion))
            changed_chunk_ids.append(str(row.get("chunk_id") or ""))
        decisions.append(row)

    non_empty = [row for row in decisions if row.get("decision")]
    non_empty_counts = Counter(str(row.get("decision") or "") for row in non_empty)
    new_counts = Counter(str(row.get("decision") or "") for row in decisions if str(row.get("chunk_id") or "") in changed_chunk_ids)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_boundary_review": approvals.get("source_boundary_review"),
        "source_base_approvals": str(args.approvals),
        "source_p2_packet": str(args.p2_packet),
        "status": "proposed_not_active",
        "instructions": [
            "This file is an automated proposal and is not read by normalize_ch10_ch11.py by default.",
            "Review every non-empty P2 decision before copying entries into ch10_ch11_source_boundary_manual_approvals.json.",
            "confirm_teaching_summary means teaching-summary support, not verbatim textbook quotation.",
            "confirm_boundary_fragment means the current boundary is acceptable as a formula/list/cross-paragraph fragment.",
        ],
        "summary": {
            "total_decisions": len(decisions),
            "non_empty_decisions": len(non_empty),
            "non_empty_by_value": dict(sorted(non_empty_counts.items())),
            "newly_proposed_p2": len(changed_chunk_ids),
            "newly_proposed_p2_by_value": dict(sorted(new_counts.items())),
            "newly_proposed_chunk_ids": changed_chunk_ids,
        },
        "decisions": decisions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": payload["status"],
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def proposed_fields(row: dict[str, Any], suggestion: dict[str, Any]) -> dict[str, Any]:
    status = str(row.get("review_status") or "")
    candidate_span = suggestion.get("candidate_span") or {}
    start = candidate_span.get("start") or row.get("approved_paragraph_start")
    end = candidate_span.get("end") or row.get("approved_paragraph_end")
    if status == "term_supported_summary_review":
        return {
            "decision": "confirm_teaching_summary",
            "approved_paragraph_start": start,
            "approved_paragraph_end": end,
            "reviewer_notes": (
                "自动建议：候选 Word 段落可作为术语锚点支撑该教学化摘要，"
                "但不标记为教材逐字引用；正式采用前仍需人工确认术语支撑是否充分。"
            ),
        }
    if status == "boundary_fragment_review":
        return {
            "decision": "confirm_boundary_fragment",
            "approved_paragraph_start": start,
            "approved_paragraph_end": end,
            "reviewer_notes": (
                "自动建议：候选 Word 段落与 Source_Chunk 属于公式、列表或跨段边界片段关系，"
                "可作为边界片段证据；正式采用前仍需人工确认是否需要拆分或补上下文。"
            ),
        }
    return {
        "decision": "manual_anchor_pending",
        "reviewer_notes": "自动建议：该条不属于 P2 标准状态，需人工回看 Word 后再决定。",
    }


if __name__ == "__main__":
    raise SystemExit(main())
