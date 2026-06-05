from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "data" / "review" / "ch10_ch11_p2_source_boundary_manual_approvals.proposed.json"
FALLBACK_BASE = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.draft.json"
DEFAULT_SCENE_PACKET = ROOT / "output" / "ch11_application_scene_review_packet_2026-06-05.json"
DEFAULT_OUTPUT = ROOT / "data" / "review" / "ch10_ch11_p3_scene_source_boundary_manual_approvals.proposed.json"
DEFAULT_SUMMARY_JSON = ROOT / "output" / "ch11_scene_proposed_approvals_summary_2026-06-05.json"
DEFAULT_SUMMARY_MD = ROOT / "output" / "ch11_scene_proposed_approvals_summary_2026-06-05.md"
DEFAULT_SUMMARY_CSV = ROOT / "output" / "ch11_scene_proposed_approvals_summary_2026-06-05.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build non-active proposed decisions for ch11 P3 application scenes.")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--scene-packet", type=Path, default=DEFAULT_SCENE_PACKET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--scene-id", default="", help="Optional scene_id to propose; default proposes every scene.")
    args = parser.parse_args()

    base_path = args.base if args.base.exists() else FALLBACK_BASE
    base = json.loads(base_path.read_text(encoding="utf-8"))
    scene_packet = json.loads(args.scene_packet.read_text(encoding="utf-8"))
    scene_index, scene_rows = load_scene_index(scene_packet, args.scene_id)
    decisions: list[dict[str, Any]] = []
    changed_chunk_ids: list[str] = []
    skipped_chunk_ids: list[str] = []
    for item in base.get("decisions", []):
        if not isinstance(item, dict):
            continue
        row = dict(item)
        scene_info = scene_index.get(item_key(row))
        if scene_info and not str(row.get("decision") or "").strip():
            row.update(proposed_fields(row, scene_info))
            changed_chunk_ids.append(str(row.get("chunk_id") or ""))
        elif scene_info:
            skipped_chunk_ids.append(str(row.get("chunk_id") or ""))
        decisions.append(row)

    summary = build_summary(decisions, scene_rows, changed_chunk_ids, skipped_chunk_ids, args.scene_id)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_boundary_review": base.get("source_boundary_review"),
        "source_base_approvals": str(base_path),
        "source_scene_packet": str(args.scene_packet),
        "status": "proposed_not_active",
        "scope_scene_id": args.scene_id or "all",
        "instructions": [
            "This file is an automated scene-batch proposal and is not read by normalize_ch10_ch11.py by default.",
            "P3 application-scene items remain manual_anchor_pending until a human reviewer confirms better textbook anchors.",
            "Do not treat these proposed decisions as formal approval or verbatim textbook evidence.",
            "Review every non-empty decision before copying entries into ch10_ch11_source_boundary_manual_approvals.json.",
        ],
        "summary": summary["approval_summary"],
        "scene_summary": summary["scene_summary"],
        "decisions": decisions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(payload_text, encoding="utf-8")
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.summary_md.write_text(render_markdown(summary, payload), encoding="utf-8")
    write_csv(args.summary_csv, summary["scene_rows"])
    print(
        json.dumps(
            {
                "output": str(args.output),
                "summary_json": str(args.summary_json),
                "summary_md": str(args.summary_md),
                "summary_csv": str(args.summary_csv),
                "status": payload["status"],
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def load_scene_index(scene_packet: dict[str, Any], scene_id_filter: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    index: dict[str, dict[str, Any]] = {}
    scene_rows: list[dict[str, Any]] = []
    for group in scene_packet.get("groups") or []:
        if not isinstance(group, dict):
            continue
        scene_id = str(group.get("scene_id") or "")
        if scene_id_filter and scene_id != scene_id_filter:
            continue
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            info = {
                "scene_id": scene_id,
                "scene_title": group.get("scene_title") or item.get("scene_title") or "",
                "scene_terms": item.get("scene_terms") or [],
                "candidate_span": item.get("candidate_span") or {},
                "candidate_score": item.get("candidate_score"),
                "score_margin": item.get("score_margin"),
            }
            key = item_key(item)
            index[key] = info
            scene_rows.append(
                {
                    "chapter_id": item.get("chapter_id"),
                    "chunk_id": item.get("chunk_id"),
                    "scene_id": scene_id,
                    "scene_title": info["scene_title"],
                    "scene_terms": info["scene_terms"],
                    "candidate_start": info["candidate_span"].get("start"),
                    "candidate_end": info["candidate_span"].get("end"),
                    "candidate_score": info["candidate_score"],
                    "score_margin": info["score_margin"],
                    "source_excerpt": item.get("source_excerpt"),
                }
            )
    return index, scene_rows


def proposed_fields(row: dict[str, Any], scene_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "manual_anchor_pending",
        "scene_id": scene_info.get("scene_id") or "",
        "scene_title": scene_info.get("scene_title") or "",
        "scene_terms": scene_info.get("scene_terms") or [],
        "reviewer_notes": (
            "自动建议：该 P3 应用场景条目仍需人工补教材锚点；当前仅按场景分组并保留为 "
            "manual_anchor_pending，不视为已确认证据。场景："
            f"{scene_info.get('scene_title') or scene_info.get('scene_id') or ''}。"
        ),
    }


def build_summary(
    decisions: list[dict[str, Any]],
    scene_rows: list[dict[str, Any]],
    changed_chunk_ids: list[str],
    skipped_chunk_ids: list[str],
    scene_id_filter: str,
) -> dict[str, Any]:
    decision_counts = Counter(str(row.get("decision") or "") for row in decisions)
    non_empty_counts = Counter(str(row.get("decision") or "") for row in decisions if str(row.get("decision") or ""))
    proposed_by_scene = Counter(row["scene_id"] for row in scene_rows if str(row.get("chunk_id") or "") in set(changed_chunk_ids))
    total = len(decisions)
    non_empty = sum(non_empty_counts.values())
    by_scene_total = Counter(row["scene_id"] for row in scene_rows)
    scene_summary = [
        {
            "scene_id": scene_id,
            "scene_title": next((row["scene_title"] for row in scene_rows if row["scene_id"] == scene_id), scene_id),
            "total": total_count,
            "newly_proposed": proposed_by_scene.get(scene_id, 0),
        }
        for scene_id, total_count in sorted(by_scene_total.items())
    ]
    return {
        "approval_summary": {
            "total_decisions": total,
            "non_empty_decisions": non_empty,
            "open_decisions": total - non_empty,
            "non_empty_by_value": dict(sorted(non_empty_counts.items())),
            "decisions_by_value": dict(sorted(decision_counts.items())),
            "newly_proposed_p3_scene": len(changed_chunk_ids),
            "skipped_existing_decisions": len(skipped_chunk_ids),
            "scope_scene_id": scene_id_filter or "all",
            "newly_proposed_chunk_ids": changed_chunk_ids,
        },
        "scene_summary": scene_summary,
        "scene_rows": scene_rows,
    }


def render_markdown(summary: dict[str, Any], payload: dict[str, Any]) -> str:
    approval = summary["approval_summary"]
    lines = [
        "# ch11 P3 场景批次 proposed 草案摘要",
        "",
        "说明：该摘要对应非正式 proposed 文件。P3 条目只保留为 manual_anchor_pending，用于提示人工补教材锚点。",
        "",
        f"- 范围：{approval['scope_scene_id']}",
        f"- 全文件 decision 条目：{approval['total_decisions']}",
        f"- 累积非空 decision：{approval['non_empty_decisions']}",
        f"- 剩余空 decision：{approval['open_decisions']}",
        f"- 本轮新增 P3 场景建议：{approval['newly_proposed_p3_scene']}",
        "",
        "## Decision 统计",
        "",
        "| decision | count |",
        "|---|---:|",
    ]
    for decision, count in approval["non_empty_by_value"].items():
        lines.append(f"| `{decision}` | {count} |")
    lines.extend(["", "## 场景统计", "", "| scene_id | scene | total | newly_proposed |", "|---|---|---:|---:|"])
    for row in summary["scene_summary"]:
        lines.append(f"| `{row['scene_id']}` | {row['scene_title']} | {row['total']} | {row['newly_proposed']} |")
    lines.extend(["", "## 输出", ""])
    lines.append(f"- proposed：`{payload.get('source_base_approvals')}` -> `{DEFAULT_OUTPUT}`")
    lines.append(f"- scene packet：`{payload.get('source_scene_packet')}`")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "chapter_id",
                "chunk_id",
                "scene_id",
                "scene_title",
                "scene_terms",
                "candidate_start",
                "candidate_end",
                "candidate_score",
                "score_margin",
                "source_excerpt",
            ],
        )
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["scene_terms"] = ";".join(str(term) for term in row.get("scene_terms") or [])
            writer.writerow(csv_row)


def item_key(item: dict[str, Any]) -> str:
    return f"{item.get('chapter_id') or ''}/{item.get('chunk_id') or ''}"


if __name__ == "__main__":
    raise SystemExit(main())
