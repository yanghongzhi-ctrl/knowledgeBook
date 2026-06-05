from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from validate_ch10_ch11_source_manual_approvals import validate_approval_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVALS = ROOT / "data" / "review" / "ch10_ch11_full_source_boundary_manual_approvals.proposed.json"
DEFAULT_BOUNDARY_REVIEW = ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.json"
DEFAULT_SCENE_PACKET = ROOT / "output" / "ch11_application_scene_review_packet_2026-06-05.json"
DEFAULT_OUTPUT_JSON = ROOT / "output" / "ch10_ch11_source_review_handoff_2026-06-05.json"
DEFAULT_OUTPUT_MD = ROOT / "output" / "ch10_ch11_source_review_handoff_2026-06-05.md"
DEFAULT_OUTPUT_CSV = ROOT / "output" / "ch10_ch11_source_review_handoff_2026-06-05.csv"


PACKET_FILES = [
    ROOT / "output" / "ch10_p1_source_review_packet_2026-06-05.json",
    ROOT / "output" / "ch10_p2_source_review_packet_2026-06-05.json",
    ROOT / "output" / "ch11_p2_quick_source_review_packet_2026-06-05.json",
    ROOT / "output" / "ch11_application_scene_review_packet_2026-06-05.json",
    ROOT / "output" / "ch11_p4_source_review_packet_2026-06-05.json",
]

DECISION_LABELS = {
    "confirm_candidate_anchor": "候选概念锚点，可人工确认后作为概念证据对应",
    "confirm_boundary_fragment": "边界片段，可人工确认后作为公式/列表/跨段片段证据",
    "confirm_teaching_summary": "教学摘要术语支撑，可人工确认后保留为非逐字摘要证据",
    "manual_anchor_pending": "仍需人工补教材锚点或维持待定",
}

REVIEW_STATUS_LABELS = {
    "candidate_anchor_review": "候选锚点复核",
    "boundary_fragment_review": "边界片段复核",
    "term_supported_summary_review": "教学摘要术语支撑复核",
    "manual_anchor_required": "需人工补教材锚点",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a handoff package for ch10/ch11 Source_Chunks review.")
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--boundary-review", type=Path, default=DEFAULT_BOUNDARY_REVIEW)
    parser.add_argument("--scene-packet", type=Path, default=DEFAULT_SCENE_PACKET)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    args = parser.parse_args()

    approvals = json.loads(args.approvals.read_text(encoding="utf-8"))
    boundary = json.loads(args.boundary_review.read_text(encoding="utf-8"))
    validation = validate_approval_payload(approvals, boundary, approvals_path=args.approvals)
    scene_index = load_scene_index(args.scene_packet)
    rows = [build_row(item, scene_index) for item in approvals.get("decisions", []) if isinstance(item, dict)]
    packet_summaries = load_packet_summaries(PACKET_FILES)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_approvals": str(args.approvals),
        "source_boundary_review": str(args.boundary_review),
        "source_scene_packet": str(args.scene_packet),
        "status": "handoff_for_human_review",
        "formal_approval_file_expected": str(ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.json"),
        "formal_approval_file_exists": (ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.json").exists(),
        "validation": validation,
        "summary": build_summary(rows, validation),
        "review_guidance": review_guidance(),
        "packet_summaries": packet_summaries,
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(args.csv, rows)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "markdown": str(args.markdown),
                "csv": str(args.csv),
                "validation_ok": validation.get("ok"),
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if validation.get("ok") else 1


def load_scene_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    packet = json.loads(path.read_text(encoding="utf-8"))
    index: dict[str, dict[str, Any]] = {}
    for group in packet.get("groups") or []:
        if not isinstance(group, dict):
            continue
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            index[item_key(item)] = {
                "scene_id": item.get("scene_id") or group.get("scene_id") or "",
                "scene_title": item.get("scene_title") or group.get("scene_title") or "",
                "scene_terms": item.get("scene_terms") or [],
            }
    return index


def load_packet_summaries(paths: list[Path]) -> list[dict[str, Any]]:
    summaries = []
    for path in paths:
        if not path.exists():
            summaries.append({"path": str(path), "exists": False})
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        summaries.append(
            {
                "path": str(path),
                "exists": True,
                "purpose": payload.get("purpose") or "",
                "summary": payload.get("summary") or {},
            }
        )
    return summaries


def build_row(item: dict[str, Any], scene_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    scene = scene_index.get(item_key(item), {})
    decision = str(item.get("decision") or "").strip()
    review_status = str(item.get("review_status") or "").strip()
    return {
        "chapter_id": item.get("chapter_id"),
        "chunk_id": item.get("chunk_id"),
        "priority_group": item.get("priority_group"),
        "review_status": review_status,
        "review_status_label": REVIEW_STATUS_LABELS.get(review_status, review_status),
        "decision": decision,
        "decision_label": DECISION_LABELS.get(decision, decision),
        "manual_review_required": manual_review_required(decision),
        "risk_level": risk_level(item),
        "scene_id": item.get("scene_id") or scene.get("scene_id") or "",
        "scene_title": item.get("scene_title") or scene.get("scene_title") or "",
        "scene_terms": item.get("scene_terms") or scene.get("scene_terms") or [],
        "approved_paragraph_start": item.get("approved_paragraph_start"),
        "approved_paragraph_end": item.get("approved_paragraph_end"),
        "candidate_score": item.get("candidate_score"),
        "score_margin": item.get("score_margin"),
        "source_excerpt_role": item.get("source_excerpt_role"),
        "source_excerpt": item.get("source_excerpt"),
        "candidate_text": item.get("candidate_text"),
        "reviewer_notes": item.get("reviewer_notes") or "",
    }


def manual_review_required(decision: str) -> str:
    if decision == "manual_anchor_pending":
        return "补教材锚点或明确保留待定"
    if decision == "confirm_teaching_summary":
        return "确认术语支撑充分且不是逐字引用"
    if decision == "confirm_boundary_fragment":
        return "确认边界片段可接受或改为拆分"
    if decision == "confirm_candidate_anchor":
        return "确认候选段落表达同一概念"
    return "补充人工判断"


def risk_level(item: dict[str, Any]) -> str:
    decision = str(item.get("decision") or "")
    status = str(item.get("review_status") or "")
    if decision == "manual_anchor_pending":
        return "high"
    if status == "boundary_fragment_review":
        return "medium"
    if status == "term_supported_summary_review":
        return "medium"
    return "low"


def build_summary(rows: list[dict[str, Any]], validation: dict[str, Any]) -> dict[str, Any]:
    decision_counts = Counter(row["decision"] or "(empty)" for row in rows)
    priority_counts = grouped_counts(rows, "priority_group")
    chapter_counts = grouped_counts(rows, "chapter_id")
    status_counts = grouped_counts(rows, "review_status")
    risk_counts = grouped_counts(rows, "risk_level")
    scene_counts = grouped_counts([row for row in rows if row.get("scene_title")], "scene_title")
    return {
        "total": len(rows),
        "validation_ok": validation.get("ok"),
        "validation_errors": len(validation.get("errors") or []),
        "validation_warnings": len(validation.get("warnings") or []),
        "decision_counts": dict(sorted(decision_counts.items())),
        "priority_counts": priority_counts,
        "chapter_counts": chapter_counts,
        "review_status_counts": status_counts,
        "risk_counts": risk_counts,
        "scene_counts": scene_counts,
        "formal_ready_without_human_review": False,
        "remaining_human_actions": [
            "逐条审定 51 条 proposed decision，尤其是 30 条 manual_anchor_pending。",
            "确认 confirm_teaching_summary 只作为教学摘要证据，不标注为教材逐字引用。",
            "确认 confirm_boundary_fragment 是否需要拆分、补上下文或保留边界片段。",
            "人工确认后，另存为 ch10_ch11_source_boundary_manual_approvals.json 并复跑 normalize/release。",
        ],
    }


def grouped_counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field) or "(empty)") for row in rows).items()))


def review_guidance() -> list[dict[str, str]]:
    return [
        {
            "decision": "confirm_candidate_anchor",
            "meaning": "概念对应候选，不等同于教材逐字引用。",
            "human_check": "确认 Source_Chunk 与候选段落表达同一概念，且段落范围准确。",
        },
        {
            "decision": "confirm_boundary_fragment",
            "meaning": "候选文本属于公式、列表或跨段边界片段。",
            "human_check": "确认是否可保留为片段；若缺公式变量或上下文，应改为 split_required 或 manual_anchor_pending。",
        },
        {
            "decision": "confirm_teaching_summary",
            "meaning": "教材中有术语或主题支撑，但 Source_Chunk 是教学化摘要。",
            "human_check": "确认术语锚点足够支撑摘要，不把该条标为逐字原文。",
        },
        {
            "decision": "manual_anchor_pending",
            "meaning": "仍需人工补更精确教材锚点或维持待定。",
            "human_check": "回看 Word 原文，补 paragraph span、改 decision，或保留待定并写清原因。",
        },
    ]


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    validation = payload["validation"]
    lines = [
        "# 第10、11章 Source_Chunks 人工复核交接包",
        "",
        "说明：本交接包汇总全量非正式 proposed 草案。它不是正式审批文件，不能直接触发 normalize/release 的人工确认逻辑。",
        "",
        f"- source proposed: `{payload['source_approvals']}`",
        f"- validation_ok: `{validation.get('ok')}`",
        f"- validation_errors: `{len(validation.get('errors') or [])}`",
        f"- validation_warnings: `{len(validation.get('warnings') or [])}`",
        f"- formal_file_exists: `{payload['formal_approval_file_exists']}`",
        f"- total review items: `{summary['total']}`",
        f"- formal_ready_without_human_review: `{summary['formal_ready_without_human_review']}`",
        "",
        "## Decision Counts",
        "",
        "| decision | count |",
        "|---|---:|",
    ]
    for decision, count in summary["decision_counts"].items():
        lines.append(f"| `{decision}` | {count} |")

    lines.extend(["", "## Risk Counts", "", "| risk | count |", "|---|---:|"])
    for risk, count in summary["risk_counts"].items():
        lines.append(f"| `{risk}` | {count} |")

    lines.extend(["", "## Priority Counts", "", "| priority | count |", "|---|---:|"])
    for priority, count in summary["priority_counts"].items():
        lines.append(f"| `{priority}` | {count} |")

    lines.extend(["", "## Scene Counts", "", "| scene | count |", "|---|---:|"])
    for scene, count in summary["scene_counts"].items():
        lines.append(f"| {scene} | {count} |")

    lines.extend(["", "## Human Review Guidance", ""])
    for item in payload["review_guidance"]:
        lines.append(f"- `{item['decision']}`：{item['meaning']} {item['human_check']}")

    lines.extend(["", "## Remaining Human Actions", ""])
    for item in summary["remaining_human_actions"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Packet Inputs", "", "| packet | exists | summary |", "|---|---|---|"])
    for packet in payload["packet_summaries"]:
        lines.append(f"| `{packet['path']}` | `{packet['exists']}` | `{json.dumps(packet.get('summary') or {}, ensure_ascii=False)}` |")
    lines.append("")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "chapter_id",
                "chunk_id",
                "priority_group",
                "review_status",
                "decision",
                "risk_level",
                "manual_review_required",
                "scene_title",
                "approved_paragraph_start",
                "approved_paragraph_end",
                "candidate_score",
                "score_margin",
                "source_excerpt_role",
                "reviewer_notes",
                "source_excerpt",
                "candidate_text",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in writer.fieldnames})


def item_key(item: dict[str, Any]) -> str:
    return f"{item.get('chapter_id') or ''}/{item.get('chunk_id') or ''}"


if __name__ == "__main__":
    raise SystemExit(main())
