from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "data" / "review" / "ch10_p2_source_boundary_manual_approvals.proposed.json"
FALLBACK_BASE = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.draft.json"
DEFAULT_CH11_PACKET = ROOT / "output" / "ch11_p2_quick_source_review_packet_2026-06-05.json"
DEFAULT_OUTPUT = ROOT / "data" / "review" / "ch10_ch11_p2_source_boundary_manual_approvals.proposed.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a cumulative non-active proposed approval file through ch11 P2.")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--ch11-packet", type=Path, default=DEFAULT_CH11_PACKET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    base_path = args.base if args.base.exists() else FALLBACK_BASE
    base = json.loads(base_path.read_text(encoding="utf-8"))
    packet = json.loads(args.ch11_packet.read_text(encoding="utf-8"))
    suggestions = {str(item.get("chunk_id") or ""): item for item in packet.get("items", [])}
    decisions = []
    changed_chunk_ids: list[str] = []
    for item in base.get("decisions", []):
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
        "source_boundary_review": base.get("source_boundary_review"),
        "source_base_approvals": str(base_path),
        "source_ch11_p2_packet": str(args.ch11_packet),
        "status": "proposed_not_active",
        "instructions": [
            "This file is an automated cumulative proposal and is not read by normalize_ch10_ch11.py by default.",
            "It preserves prior proposed decisions from the base file and adds ch11 P2 quick-confirm suggestions.",
            "Review every non-empty decision before copying entries into ch10_ch11_source_boundary_manual_approvals.json.",
            "Confirmed anchors mean concept correspondence only, not verbatim textbook quotes.",
        ],
        "summary": {
            "total_decisions": len(decisions),
            "non_empty_decisions": len(non_empty),
            "non_empty_by_value": dict(sorted(non_empty_counts.items())),
            "newly_proposed_ch11_p2": len(changed_chunk_ids),
            "newly_proposed_ch11_p2_by_value": dict(sorted(new_counts.items())),
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
    if status == "candidate_anchor_review":
        return {
            "decision": "confirm_candidate_anchor",
            "approved_paragraph_start": start,
            "approved_paragraph_end": end,
            "reviewer_notes": (
                "自动建议：Source_Chunk 与候选 Word 段落表达同一概念，可作为概念证据对应；"
                "不标记为教材逐字引用，最终仍需人工复核确认。"
            ),
        }
    return {
        "decision": "manual_anchor_pending",
        "reviewer_notes": "自动建议：该条不属于 candidate_anchor_review，需人工回看 Word 后再决定。",
    }


if __name__ == "__main__":
    raise SystemExit(main())
