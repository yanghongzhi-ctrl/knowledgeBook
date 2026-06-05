from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVALS = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.draft.json"
DEFAULT_SCENE_PACKET = ROOT / "output" / "ch11_application_scene_review_packet_2026-06-05.json"
DEFAULT_OUTPUT_JSON = ROOT / "output" / "ch10_ch11_source_review_progress_2026-06-05.json"
DEFAULT_OUTPUT_MD = ROOT / "output" / "ch10_ch11_source_review_progress_2026-06-05.md"

PRIORITY_ORDER = {
    "P1_ch10_quick_confirm": 1,
    "P1_ch10_formula_gap": 2,
    "P2_ch10_boundary_summary": 3,
    "P2_ch11_quick_confirm": 4,
    "P3_ch11_application_scene_manual": 5,
    "P4_ch11_boundary_summary": 6,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Report ch10/ch11 Source_Chunks manual review progress.")
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--scene-packet", type=Path, default=DEFAULT_SCENE_PACKET)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--next-limit", type=int, default=12)
    args = parser.parse_args()

    approvals = json.loads(args.approvals.read_text(encoding="utf-8"))
    scene_index = load_scene_index(args.scene_packet)
    items = [enrich_item(item, scene_index) for item in approvals.get("decisions", []) if isinstance(item, dict)]
    payload = build_report(items, args.approvals, args.scene_packet, args.next_limit)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")

    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "markdown": str(args.markdown),
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def load_scene_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    index: dict[str, dict[str, Any]] = {}
    for group in payload.get("groups") or []:
        if not isinstance(group, dict):
            continue
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            key = item_key(item)
            index[key] = {
                "scene_id": item.get("scene_id") or group.get("scene_id") or "",
                "scene_title": item.get("scene_title") or group.get("scene_title") or "",
                "scene_terms": item.get("scene_terms") or [],
            }
    return index


def enrich_item(item: dict[str, Any], scene_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    enriched = dict(item)
    enriched.update(scene_index.get(item_key(item), {}))
    enriched["decision"] = str(item.get("decision") or "").strip()
    enriched["is_open"] = not bool(enriched["decision"])
    return enriched


def build_report(items: list[dict[str, Any]], approvals_path: Path, scene_packet_path: Path, next_limit: int) -> dict[str, Any]:
    total = len(items)
    filled = sum(1 for item in items if not item["is_open"])
    open_items = [item for item in items if item["is_open"]]
    by_priority = grouped_progress(items, "priority_group")
    by_chapter = grouped_progress(items, "chapter_id")
    by_scene = grouped_progress([item for item in items if item.get("scene_title")], "scene_title")
    next_items = sorted(open_items, key=next_item_sort_key)[: max(0, next_limit)]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_approvals": str(approvals_path),
        "source_scene_packet": str(scene_packet_path),
        "summary": {
            "total": total,
            "filled": filled,
            "open": len(open_items),
            "completion_percent": round((filled / total) * 100, 2) if total else 0,
            "decisions": dict(sorted(Counter(item["decision"] or "(empty)" for item in items).items())),
        },
        "by_chapter": by_chapter,
        "by_priority": by_priority,
        "by_scene": by_scene,
        "next_items": [compact_item(item) for item in next_items],
    }


def grouped_progress(items: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[str(item.get(field) or "(empty)")].append(item)
    rows = []
    for key, rows_items in groups.items():
        total = len(rows_items)
        filled = sum(1 for item in rows_items if not item["is_open"])
        rows.append(
            {
                "name": key,
                "total": total,
                "filled": filled,
                "open": total - filled,
                "completion_percent": round((filled / total) * 100, 2) if total else 0,
            }
        )
    return sorted(rows, key=lambda row: group_sort_key(field, row["name"]))


def next_item_sort_key(item: dict[str, Any]) -> tuple[int, str, int, str]:
    priority = str(item.get("priority_group") or "")
    scene = str(item.get("scene_title") or "")
    start = safe_int(item.get("approved_paragraph_start"))
    return (PRIORITY_ORDER.get(priority, 99), scene, start, str(item.get("chunk_id") or ""))


def group_sort_key(field: str, name: str) -> tuple[int, str]:
    if field == "priority_group":
        return (PRIORITY_ORDER.get(name, 99), name)
    return (0, name)


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "chapter_id": item.get("chapter_id"),
        "chunk_id": item.get("chunk_id"),
        "priority_group": item.get("priority_group"),
        "scene_title": item.get("scene_title") or "",
        "review_status": item.get("review_status"),
        "suggested_decision": item.get("suggested_decision"),
        "candidate_span": [
            item.get("approved_paragraph_start"),
            item.get("approved_paragraph_end"),
        ],
        "source_excerpt": str(item.get("source_excerpt") or "")[:180],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# 第10、11章 Source_Chunks 人工复核进度",
        "",
        f"- total: {summary['total']}",
        f"- filled: {summary['filled']}",
        f"- open: {summary['open']}",
        f"- completion: {summary['completion_percent']}%",
        "",
        "## Priority Progress",
        "",
        "| priority | filled | open | total | complete |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in payload["by_priority"]:
        lines.append(
            f"| `{row['name']}` | {row['filled']} | {row['open']} | {row['total']} | {row['completion_percent']}% |"
        )
    lines.extend(["", "## Scene Progress", "", "| scene | filled | open | total | complete |", "|---|---:|---:|---:|---:|"])
    for row in payload["by_scene"]:
        lines.append(f"| {row['name']} | {row['filled']} | {row['open']} | {row['total']} | {row['completion_percent']}% |")
    lines.extend(["", "## Next Items", ""])
    for item in payload["next_items"]:
        scene = f" / {item['scene_title']}" if item.get("scene_title") else ""
        lines.extend(
            [
                f"### {item['chunk_id']} / {item['priority_group']}{scene}",
                "",
                f"- review_status: `{item['review_status']}`",
                f"- suggested_decision: `{item['suggested_decision']}`",
                f"- candidate_span: `{item['candidate_span'][0]}-{item['candidate_span'][1]}`",
                "",
                quote(item.get("source_excerpt") or ""),
                "",
            ]
        )
    return "\n".join(lines)


def quote(text: str) -> str:
    cleaned = str(text).strip()
    if not cleaned:
        return "> "
    return "\n".join("> " + line for line in cleaned.splitlines())


def item_key(item: dict[str, Any]) -> str:
    return f"{item.get('chapter_id') or ''}/{item.get('chunk_id') or ''}"


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
