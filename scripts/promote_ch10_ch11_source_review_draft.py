from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from validate_ch10_ch11_source_manual_approvals import validate_approval_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFT = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.draft.json"
DEFAULT_FORMAL = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.json"
DEFAULT_BOUNDARY_REVIEW = ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.json"
DEFAULT_PREVIEW_JSON = ROOT / "output" / "ch10_ch11_source_boundary_draft_promotion_preview_2026-06-05.json"
DEFAULT_PREVIEW_MD = ROOT / "output" / "ch10_ch11_source_boundary_draft_promotion_preview_2026-06-05.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview or promote ch10/ch11 Source_Chunks review draft approvals to the formal approval file."
    )
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--formal", type=Path, default=DEFAULT_FORMAL)
    parser.add_argument("--boundary-review", type=Path, default=DEFAULT_BOUNDARY_REVIEW)
    parser.add_argument("--preview-json", type=Path, default=DEFAULT_PREVIEW_JSON)
    parser.add_argument("--preview-md", type=Path, default=DEFAULT_PREVIEW_MD)
    parser.add_argument("--write-formal", action="store_true")
    parser.add_argument("--confirm-reviewed", action="store_true")
    parser.add_argument("--allow-overwrite", action="store_true")
    parser.add_argument("--print-full", action="store_true")
    args = parser.parse_args()

    result = build_preview(args.draft, args.formal, args.boundary_review)
    args.preview_json.parent.mkdir(parents=True, exist_ok=True)
    args.preview_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.preview_md.write_text(render_markdown(result), encoding="utf-8")

    write_errors = formal_write_errors(result, args)
    if args.write_formal and not write_errors:
        args.formal.parent.mkdir(parents=True, exist_ok=True)
        formal_payload = json.loads(args.draft.read_text(encoding="utf-8"))
        formal_payload["status"] = "manual_review_formal"
        formal_payload["promoted_from"] = str(args.draft)
        formal_payload["promoted_at"] = datetime.now().isoformat(timespec="seconds")
        formal_payload["promotion_note"] = "Created by promote_ch10_ch11_source_review_draft.py after explicit review confirmation."
        args.formal.write_text(json.dumps(formal_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["formal_written"] = True
        result["formal_written_at"] = datetime.now().isoformat(timespec="seconds")
        args.preview_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.preview_md.write_text(render_markdown(result), encoding="utf-8")
    else:
        result["formal_written"] = False
        result["formal_write_blockers"] = write_errors
        args.preview_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.preview_md.write_text(render_markdown(result), encoding="utf-8")

    print_payload = result if args.print_full else console_summary(result, args.preview_json, args.preview_md)
    print(json.dumps(print_payload, ensure_ascii=False, indent=2))
    if args.write_formal and write_errors:
        return 1
    return 0 if result["validation"]["ok"] else 1


def build_preview(draft_path: Path, formal_path: Path, boundary_path: Path) -> dict[str, Any]:
    if not draft_path.exists():
        return {
            "ok": False,
            "mode": "preview",
            "draft": str(draft_path),
            "formal": str(formal_path),
            "formal_exists": formal_path.exists(),
            "validation": {
                "ok": False,
                "errors": [f"Draft approval file not found: {draft_path}"],
                "warnings": [],
                "summary": {},
            },
            "summary": {},
            "open_items": [],
        }

    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    validation = validate_approval_payload(draft, boundary, approvals_path=draft_path)
    decisions = draft.get("decisions") if isinstance(draft, dict) else []
    if not isinstance(decisions, list):
        decisions = []

    known_total = count_known_items(boundary)
    priority_counts: Counter[str] = Counter()
    priority_open: Counter[str] = Counter()
    chapter_counts: Counter[str] = Counter()
    chapter_open: Counter[str] = Counter()
    open_items: list[dict[str, Any]] = []

    for item in decisions:
        if not isinstance(item, dict):
            continue
        chapter_id = str(item.get("chapter_id") or "")
        priority = str(item.get("priority_group") or "unknown")
        decision = str(item.get("decision") or "").strip()
        priority_counts[priority] += 1
        chapter_counts[chapter_id] += 1
        if not decision:
            priority_open[priority] += 1
            chapter_open[chapter_id] += 1
            open_items.append(
                {
                    "chapter_id": chapter_id,
                    "chunk_id": item.get("chunk_id"),
                    "priority_group": priority,
                    "review_status": item.get("review_status"),
                    "suggested_decision": item.get("suggested_decision"),
                }
            )

    non_empty = int(validation.get("summary", {}).get("non_empty_decisions") or 0)
    return {
        "ok": bool(validation["ok"]),
        "mode": "preview",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "draft": str(draft_path),
        "formal": str(formal_path),
        "formal_exists": formal_path.exists(),
        "validation": validation,
        "summary": {
            "known_review_items": known_total,
            "draft_items": len(decisions),
            "non_empty_decisions": non_empty,
            "open_decisions": len(open_items),
            "chapters": {
                chapter: {
                    "items": count,
                    "open": chapter_open.get(chapter, 0),
                    "filled": count - chapter_open.get(chapter, 0),
                }
                for chapter, count in sorted(chapter_counts.items())
            },
            "priorities": {
                priority: {
                    "items": count,
                    "open": priority_open.get(priority, 0),
                    "filled": count - priority_open.get(priority, 0),
                }
                for priority, count in sorted(priority_counts.items())
            },
        },
        "open_items": open_items,
        }


def console_summary(result: dict[str, Any], preview_json: Path, preview_md: Path) -> dict[str, Any]:
    validation = result.get("validation") or {}
    summary = result.get("summary") or {}
    return {
        "ok": result.get("ok"),
        "formal_written": result.get("formal_written", False),
        "formal_write_blockers": result.get("formal_write_blockers", []),
        "validation_ok": validation.get("ok"),
        "validation_errors": validation.get("errors", []),
        "validation_warnings": validation.get("warnings", []),
        "non_empty_decisions": summary.get("non_empty_decisions", 0),
        "open_decisions": summary.get("open_decisions", 0),
        "preview_json": str(preview_json),
        "preview_md": str(preview_md),
    }


def formal_write_errors(result: dict[str, Any], args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    if not args.write_formal:
        errors.append("Dry run only. Add --write-formal --confirm-reviewed to write the formal approval file.")
        return errors
    if not args.confirm_reviewed:
        errors.append("Writing formal approvals requires --confirm-reviewed.")
    if not result["validation"]["ok"]:
        errors.append("Draft validation did not pass.")
    if result.get("formal_exists") and not args.allow_overwrite:
        errors.append("Formal approval file already exists. Add --allow-overwrite to replace it.")
    return errors


def count_known_items(boundary: dict[str, Any]) -> int:
    total = 0
    for chapter in (boundary.get("chapters") or {}).values():
        if isinstance(chapter, dict):
            total += len(chapter.get("source_boundary_reviews") or [])
    return total


def render_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary") or {}
    validation = result.get("validation") or {}
    lines = [
        "# 第10、11章 Source_Chunks 审批草稿晋级预检",
        "",
        f"- draft: `{result.get('draft')}`",
        f"- formal: `{result.get('formal')}`",
        f"- formal_exists: `{result.get('formal_exists')}`",
        f"- validation_ok: `{validation.get('ok')}`",
        f"- non_empty_decisions: `{summary.get('non_empty_decisions', 0)}`",
        f"- open_decisions: `{summary.get('open_decisions', 0)}`",
        f"- formal_written: `{result.get('formal_written', False)}`",
        "",
        "## Decision Summary",
        "",
        "| decision | count |",
        "|---|---:|",
    ]
    for decision, count in (validation.get("summary", {}).get("decisions_by_value") or {}).items():
        label = decision or "(empty)"
        lines.append(f"| `{label}` | {count} |")

    lines.extend(["", "## Priority Progress", "", "| priority | filled | open | total |", "|---|---:|---:|---:|"])
    for priority, row in (summary.get("priorities") or {}).items():
        lines.append(f"| `{priority}` | {row.get('filled', 0)} | {row.get('open', 0)} | {row.get('items', 0)} |")

    blockers = result.get("formal_write_blockers") or []
    if blockers:
        lines.extend(["", "## Formal Write Blockers", ""])
        lines.extend(f"- {item}" for item in blockers)

    errors = validation.get("errors") or []
    warnings = validation.get("warnings") or []
    if errors:
        lines.extend(["", "## Validation Errors", ""])
        lines.extend(f"- {item}" for item in errors)
    if warnings:
        lines.extend(["", "## Validation Warnings", ""])
        lines.extend(f"- {item}" for item in warnings)

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
