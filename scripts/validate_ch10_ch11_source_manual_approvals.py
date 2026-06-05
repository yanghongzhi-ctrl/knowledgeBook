from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVALS = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.json"
DEFAULT_BOUNDARY_REVIEW = ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.json"

ALLOWED_DECISIONS = {
    "",
    "confirm_candidate_anchor",
    "confirm_teaching_summary",
    "confirm_boundary_fragment",
    "split_required",
    "reject_candidate",
    "manual_anchor_pending",
}

CONFIRM_DECISIONS = {
    "confirm_candidate_anchor",
    "confirm_teaching_summary",
    "confirm_boundary_fragment",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ch10/ch11 Source_Chunks manual approval decisions.")
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--boundary-review", type=Path, default=DEFAULT_BOUNDARY_REVIEW)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    if not args.approvals.exists():
        result = {
            "ok": bool(args.allow_missing),
            "approvals": str(args.approvals),
            "errors": [] if args.allow_missing else [f"Approval file not found: {args.approvals}"],
            "warnings": ["Approval file is missing; no manual decisions will be applied."] if args.allow_missing else [],
            "summary": {},
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    approvals = json.loads(args.approvals.read_text(encoding="utf-8"))
    boundary = json.loads(args.boundary_review.read_text(encoding="utf-8"))
    result = validate_approval_payload(approvals, boundary, approvals_path=args.approvals)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def validate_approval_payload(
    approvals: dict[str, Any],
    boundary: dict[str, Any],
    approvals_path: Path | str | None = None,
) -> dict[str, Any]:
    if not isinstance(approvals, dict):
        return {
            "ok": False,
            "approvals": str(approvals_path) if approvals_path is not None else "",
            "errors": ["approvals must be a JSON object"],
            "warnings": [],
            "summary": {},
        }
    known = known_review_items(boundary)
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()
    decisions = approvals.get("decisions")
    if not isinstance(decisions, list):
        errors.append("approvals.decisions must be a list")
        decisions = []

    counts: Counter[str] = Counter()
    applied_counts: Counter[str] = Counter()
    for index, item in enumerate(decisions, 1):
        if not isinstance(item, dict):
            errors.append(f"decisions[{index}] must be an object")
            continue
        chapter_id = str(item.get("chapter_id") or "").strip()
        chunk_id = str(item.get("chunk_id") or "").strip()
        decision = str(item.get("decision") or "").strip()
        key = (chapter_id, chunk_id)
        counts[decision] += 1
        if decision:
            applied_counts[decision] += 1
        if not chapter_id or not chunk_id:
            errors.append(f"decisions[{index}] missing chapter_id or chunk_id")
            continue
        if key in seen:
            errors.append(f"Duplicate approval decision for {chapter_id}/{chunk_id}")
        seen.add(key)
        if key not in known:
            errors.append(f"Unknown review item: {chapter_id}/{chunk_id}")
            continue
        if decision not in ALLOWED_DECISIONS:
            errors.append(f"{chapter_id}/{chunk_id} has invalid decision: {decision}")
            continue
        if not decision:
            continue
        expected = str(known[key].get("review_status") or "")
        validate_decision_matches_status(chapter_id, chunk_id, decision, expected, errors, warnings)
        if decision in CONFIRM_DECISIONS:
            validate_paragraph_span(chapter_id, chunk_id, item, errors)
            if not str(item.get("reviewer_notes") or "").strip():
                warnings.append(f"{chapter_id}/{chunk_id} confirmation has no reviewer_notes")

    result = {
        "ok": not errors,
        "approvals": str(approvals_path) if approvals_path is not None else "",
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "items": len(decisions),
            "decisions_by_value": dict(sorted(counts.items())),
            "non_empty_decisions": sum(applied_counts.values()),
            "non_empty_by_value": dict(sorted(applied_counts.items())),
        },
    }
    return result


def known_review_items(boundary: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    known: dict[tuple[str, str], dict[str, Any]] = {}
    for chapter_id, chapter in (boundary.get("chapters") or {}).items():
        if not isinstance(chapter, dict):
            continue
        for item in chapter.get("source_boundary_reviews") or []:
            if isinstance(item, dict):
                known[(str(chapter_id), str(item.get("chunk_id") or ""))] = item
    return known


def validate_decision_matches_status(
    chapter_id: str,
    chunk_id: str,
    decision: str,
    expected_status: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    expected_decisions = {
        "candidate_anchor_review": {"confirm_candidate_anchor", "reject_candidate", "manual_anchor_pending"},
        "term_supported_summary_review": {"confirm_teaching_summary", "reject_candidate", "manual_anchor_pending"},
        "boundary_fragment_review": {"confirm_boundary_fragment", "split_required", "manual_anchor_pending"},
        "manual_anchor_required": {"manual_anchor_pending", "confirm_candidate_anchor", "reject_candidate"},
    }
    allowed = expected_decisions.get(expected_status, set())
    if allowed and decision not in allowed:
        warnings.append(
            f"{chapter_id}/{chunk_id} decision {decision} is unusual for review_status {expected_status}; allowed usual values: {sorted(allowed)}"
        )


def validate_paragraph_span(chapter_id: str, chunk_id: str, item: dict[str, Any], errors: list[str]) -> None:
    start = item.get("approved_paragraph_start")
    end = item.get("approved_paragraph_end")
    try:
        start_num = int(start)
        end_num = int(end)
    except (TypeError, ValueError):
        errors.append(f"{chapter_id}/{chunk_id} confirmation requires numeric approved_paragraph_start/end")
        return
    if start_num <= 0 or end_num < start_num:
        errors.append(f"{chapter_id}/{chunk_id} has invalid approved paragraph range: {start}-{end}")


if __name__ == "__main__":
    raise SystemExit(main())
