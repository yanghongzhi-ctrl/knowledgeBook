from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.template.json"
DEFAULT_P1_PACKET = ROOT / "output" / "ch10_p1_source_review_packet_2026-06-05.json"
DEFAULT_OUTPUT = ROOT / "data" / "review" / "ch10_p1_source_boundary_manual_approvals.proposed.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a non-active proposed approval file for ch10 P1 Source_Chunks.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--p1-packet", type=Path, default=DEFAULT_P1_PACKET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    template = json.loads(args.template.read_text(encoding="utf-8"))
    packet = json.loads(args.p1_packet.read_text(encoding="utf-8"))
    suggestions = {str(item.get("chunk_id") or ""): item for item in packet.get("items", [])}
    decisions = []
    for item in template.get("decisions", []):
        if not isinstance(item, dict):
            continue
        row = dict(item)
        suggestion = suggestions.get(str(row.get("chunk_id") or ""))
        if suggestion:
            row.update(proposed_fields(row, suggestion))
        decisions.append(row)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_boundary_review": template.get("source_boundary_review"),
        "source_p1_packet": str(args.p1_packet),
        "status": "proposed_not_active",
        "instructions": [
            "This file is an automated proposal and is not read by normalize_ch10_ch11.py by default.",
            "Review every non-empty decision before copying entries into ch10_ch11_source_boundary_manual_approvals.json.",
            "Confirmed anchors mean concept correspondence only, not verbatim textbook quotes.",
        ],
        "decisions": decisions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    filled = [row for row in decisions if row.get("decision")]
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": payload["status"],
                "total": len(decisions),
                "proposed_decisions": len(filled),
                "proposed_chunk_ids": [row.get("chunk_id") for row in filled],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def proposed_fields(row: dict[str, Any], suggestion: dict[str, Any]) -> dict[str, Any]:
    priority = str(row.get("priority_group") or "")
    if priority == "P1_ch10_formula_gap":
        return {
            "decision": "manual_anchor_pending",
            "reviewer_notes": "自动建议：该条疑似公式/变量残缺，应回看 Word 原文并决定补上下文、拆分或重写边界；暂不确认候选锚点。",
        }
    return {
        "decision": "confirm_candidate_anchor",
        "reviewer_notes": (
            "自动建议：Source_Chunk 与候选 Word 段落表达同一概念，可作为概念依据对应；"
            "不标记为教材逐字引用，最终仍需人工复核确认。"
        ),
        "approved_paragraph_start": suggestion.get("candidate_span", {}).get("start") or row.get("approved_paragraph_start"),
        "approved_paragraph_end": suggestion.get("candidate_span", {}).get("end") or row.get("approved_paragraph_end"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
