from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "output" / "evidence_quality_audit_2026-06-05.json"
DEFAULT_MD = ROOT / "output" / "evidence_quality_audit_2026-06-05.md"
DEFAULT_CHAPTERS = tuple(f"ch{index:02d}" for index in range(1, 12))
EVIDENCE_CHAPTERS = {"ch06", "ch07", "ch08", "ch09", "ch10", "ch11"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit evidence grading fields across textbook knowledge packages.")
    parser.add_argument("--chapters", nargs="+", default=list(DEFAULT_CHAPTERS))
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    chapters = [audit_chapter(chapter_id) for chapter_id in args.chapters]
    report = {
        "scope": "ch01-ch11 evidence quality audit; ch06-ch11 include Word evidence grading checks",
        "policy": (
            "This audit is an automated maintenance signal for a fixed textbook knowledge base. "
            "Low confidence or weak anchors are tracked as quality buckets, not manual approval blockers."
        ),
        "chapters": chapters,
        "summary": summarize(chapters),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"json={args.output_json}")
    print(f"md={args.output_md}")
    return 0


def audit_chapter(chapter_id: str) -> dict[str, Any]:
    package_path = next((ROOT / "data" / "raw" / chapter_id).glob("*.json"), None)
    if package_path is None:
        return {"chapter_id": chapter_id, "exists": False, "issues": ["missing_package"]}

    data = json.loads(package_path.read_text(encoding="utf-8"))
    source_rows = [row for row in data.get("Source_Chunks", []) if isinstance(row, dict)]
    answer_rows = [row for row in data.get("Answer_Cards", []) if isinstance(row, dict)]
    resources = [row for row in data.get("Resources", []) if isinstance(row, dict)]
    source_profiles = [source_quality(chapter_id, row) for row in source_rows]
    answer_profiles = [answer_quality(row) for row in answer_rows]
    release = read_release_summary(chapter_id)

    source_confidence = Counter(profile["confidence"] for profile in source_profiles)
    answer_support = Counter(profile["support_type"] for profile in answer_profiles)
    word_status = Counter(profile["word_status"] for profile in source_profiles)
    source_review = Counter(profile["review_status"] for profile in source_profiles)

    source_needs_anchor = [profile for profile in source_profiles if profile["needs_textbook_anchor_review"]]
    answer_needs_anchor = [profile for profile in answer_profiles if profile["needs_textbook_anchor_review"]]
    text_issues = detect_text_issues(source_rows)
    field_issues = field_integrity_issues(chapter_id, source_profiles, answer_profiles)

    return {
        "chapter_id": chapter_id,
        "exists": True,
        "package_path": package_path.relative_to(ROOT).as_posix(),
        "chapter_title": chapter_title(data, chapter_id),
        "kb_type": (data.get("metadata") or {}).get("kb_type") if isinstance(data.get("metadata"), dict) else "",
        "source_chunks": len(source_rows),
        "answer_cards": len(answer_rows),
        "resources": len(resources),
        "release": release,
        "source_confidence": dict(source_confidence),
        "source_word_status": dict(word_status),
        "source_review_status": dict(source_review),
        "answer_support_type": dict(answer_support),
        "answer_confidence": dict(Counter(profile["confidence"] for profile in answer_profiles)),
        "source_needs_textbook_anchor_review": len(source_needs_anchor),
        "answer_needs_textbook_anchor_review": len(answer_needs_anchor),
        "text_issues": text_issues,
        "field_issues": field_issues,
        "follow_up_candidates": {
            "source_chunks": source_needs_anchor[:12],
            "answer_cards": answer_needs_anchor[:12],
        },
    }


def source_quality(chapter_id: str, row: dict[str, Any]) -> dict[str, Any]:
    profile = row.get("evidence_quality_profile") if isinstance(row.get("evidence_quality_profile"), dict) else {}
    word_alignment = row.get("word_alignment") if isinstance(row.get("word_alignment"), dict) else {}
    word_correspondence = row.get("word_correspondence") if isinstance(row.get("word_correspondence"), dict) else {}

    has_word_fields = bool(profile or word_alignment or word_correspondence or row.get("word_verification"))
    raw_status = str(
        profile.get("word_verification")
        or row.get("word_verification")
        or word_alignment.get("status")
        or word_correspondence.get("status")
        or ("missing" if chapter_id in EVIDENCE_CHAPTERS else "ungraded")
    )
    alignment_status = str(word_alignment.get("status") or word_correspondence.get("status") or "")
    confidence = str(
        profile.get("evidence_confidence")
        or ("ungraded" if not has_word_fields else confidence_from_alignment(alignment_status, raw_status))
    )
    review_status = str(profile.get("review_status") or row.get("review_status") or "missing")
    needs_anchor = bool(profile.get("needs_textbook_anchor_review"))
    if not profile and alignment_status == "missing":
        needs_anchor = True
    if raw_status in {"auto_anchor_missing_or_weak", "missing"} and alignment_status == "missing":
        needs_anchor = True

    return {
        "chunk_id": str(row.get("chunk_id") or row.get("source_id") or ""),
        "title": str(row.get("title") or row.get("heading") or row.get("chunk_summary") or "")[:120],
        "confidence": confidence,
        "word_status": raw_status,
        "alignment_status": alignment_status or "missing",
        "boundary_type": str(profile.get("evidence_boundary_type") or alignment_status or "missing"),
        "review_status": review_status,
        "source_excerpt_role": str(profile.get("source_excerpt_role") or row.get("source_excerpt_role") or "missing"),
        "usable_for_answer": str(profile.get("usable_for_answer") or row.get("usable_for_answer") or "missing"),
        "needs_textbook_anchor_review": needs_anchor,
    }


def confidence_from_alignment(alignment_status: str, raw_status: str) -> str:
    status = alignment_status or raw_status
    if status in {"exact", "auto_direct_text_supported"}:
        return "high"
    if status in {
        "partial",
        "concept_supported",
        "auto_partial_text_supported",
        "auto_concept_operation_supported",
        "auto_concept_anchor_supported",
        "auto_teaching_summary_supported",
        "auto_boundary_fragment_supported",
    }:
        return "medium"
    if status in {"missing", "auto_anchor_missing_or_weak", "auto_operation_summary_not_direct_quote"}:
        return "low"
    return "ungraded"


def answer_quality(row: dict[str, Any]) -> dict[str, Any]:
    word_alignment = row.get("word_alignment") if isinstance(row.get("word_alignment"), dict) else {}
    support_type = str(word_alignment.get("support_type") or "ungraded")
    confidence = str(word_alignment.get("evidence_confidence") or ("low" if "missing" in support_type else "ungraded"))
    needs_anchor = bool(word_alignment.get("needs_textbook_anchor_review")) or support_type == "word_direct_question_missing"
    return {
        "answer_id": str(row.get("answer_id") or ""),
        "canonical_question": str(row.get("canonical_question") or "")[:140],
        "support_type": support_type,
        "confidence": confidence,
        "needs_textbook_anchor_review": needs_anchor,
    }


def detect_text_issues(source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    issue_patterns = {
        "word_xml_residue": re.compile(r"</?w:|<w\\b"),
        "duplicate_period_fragment": re.compile(r"。。+"),
        "known_bad_fragment": re.compile(r"转型。的"),
        "source_repair_placeholder": re.compile(r"残留Word XML格式内容"),
    }
    issue_rows: dict[str, list[dict[str, str]]] = {key: [] for key in issue_patterns}
    for row in source_rows:
        text = "\n".join(str(row.get(field) or "") for field in ("source_excerpt", "chunk_summary", "summary", "evidence_boundary_note"))
        for key, pattern in issue_patterns.items():
            if pattern.search(text):
                issue_rows[key].append(
                    {
                        "chunk_id": str(row.get("chunk_id") or row.get("source_id") or ""),
                        "preview": compact(text)[:160],
                    }
                )
    return {
        key: {"count": len(rows), "samples": rows[:5]}
        for key, rows in issue_rows.items()
        if rows
    }


def field_integrity_issues(
    chapter_id: str,
    source_profiles: list[dict[str, Any]],
    answer_profiles: list[dict[str, Any]],
) -> dict[str, int]:
    issues: Counter[str] = Counter()
    if chapter_id in EVIDENCE_CHAPTERS:
        for profile in source_profiles:
            if profile["alignment_status"] == "missing" and profile["word_status"] == "missing":
                issues["source_missing_word_alignment"] += 1
            if profile["usable_for_answer"] != "no_direct_output":
                issues["source_direct_output_policy_not_explicit"] += 1
        for profile in answer_profiles:
            if profile["support_type"] == "ungraded" and chapter_id in {"ch06", "ch07", "ch08", "ch09"}:
                issues["answer_missing_word_alignment"] += 1
    return dict(issues)


def read_release_summary(chapter_id: str) -> dict[str, Any]:
    path = ROOT / "output" / f"{chapter_id}_rag_engine" / "reports" / f"release_report_{chapter_id}.json"
    if not path.exists():
        return {"exists": False}
    report = json.loads(path.read_text(encoding="utf-8"))
    steps = report.get("steps") or []
    return {
        "exists": True,
        "status": report.get("status") or report.get("release_status") or "",
        "version_id": report.get("version_id") or "",
        "failed_steps": [
            str(step.get("name") or step.get("step"))
            for step in steps
            if isinstance(step, dict) and str(step.get("status")) not in {"passed", "released", "skipped"}
        ],
    }


def chapter_title(data: dict[str, Any], chapter_id: str) -> str:
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    if metadata.get("chapter_title"):
        return str(metadata["chapter_title"])
    for row in data.get("Chapter_Structure", []):
        if isinstance(row, dict) and str(row.get("chapter_id") or "") == chapter_id and row.get("title"):
            return str(row["title"])
    return chapter_id


def summarize(chapters: list[dict[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    attention = []
    for chapter in chapters:
        if not chapter.get("exists"):
            attention.append({"chapter_id": chapter["chapter_id"], "issue": "missing_package"})
            continue
        totals["source_chunks"] += int(chapter.get("source_chunks") or 0)
        totals["answer_cards"] += int(chapter.get("answer_cards") or 0)
        totals["source_needs_textbook_anchor_review"] += int(chapter.get("source_needs_textbook_anchor_review") or 0)
        totals["answer_needs_textbook_anchor_review"] += int(chapter.get("answer_needs_textbook_anchor_review") or 0)
        if chapter.get("text_issues"):
            attention.append({"chapter_id": chapter["chapter_id"], "issue": "text_issue", "details": chapter["text_issues"]})
        if chapter.get("field_issues"):
            attention.append({"chapter_id": chapter["chapter_id"], "issue": "field_integrity", "details": chapter["field_issues"]})
    return {
        "chapters": len(chapters),
        "source_chunks": totals["source_chunks"],
        "answer_cards": totals["answer_cards"],
        "source_needs_textbook_anchor_review": totals["source_needs_textbook_anchor_review"],
        "answer_needs_textbook_anchor_review": totals["answer_needs_textbook_anchor_review"],
        "attention_items": attention,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Evidence Quality Audit",
        "",
        "This report summarizes automated textbook evidence grading. Low confidence entries are quality buckets, not approval blockers.",
        "",
        "## Chapter Summary",
        "",
        "| Chapter | Sources | Source Confidence | Source Needs Anchor | Answers | Answer Support | Answer Needs Anchor | Release | Field Issues |",
        "|---|---:|---|---:|---:|---|---:|---|---|",
    ]
    for chapter in report["chapters"]:
        if not chapter.get("exists"):
            lines.append(f"| {chapter['chapter_id']} | 0 | missing | 0 | 0 | missing | 0 | missing | missing_package |")
            continue
        lines.append(
            "| {chapter_id} | {sources} | {source_confidence} | {source_needs} | {answers} | {answer_support} | {answer_needs} | {release} | {field_issues} |".format(
                chapter_id=chapter["chapter_id"],
                sources=chapter["source_chunks"],
                source_confidence=format_counts(chapter.get("source_confidence") or {}),
                source_needs=chapter["source_needs_textbook_anchor_review"],
                answers=chapter["answer_cards"],
                answer_support=format_counts(chapter.get("answer_support_type") or {}),
                answer_needs=chapter["answer_needs_textbook_anchor_review"],
                release=chapter.get("release", {}).get("status") or "unknown",
                field_issues=format_counts(chapter.get("field_issues") or {}) or "-",
            )
        )
    lines.extend(["", "## Attention Buckets", ""])
    summary = report["summary"]
    if not summary["attention_items"]:
        lines.append("No text residue or field integrity issues were detected.")
    else:
        for item in summary["attention_items"]:
            lines.append(f"- `{item['chapter_id']}` {item['issue']}: {format_attention_details(item.get('details', {}))}")
    lines.extend(["", "## Follow-Up Candidates", ""])
    for chapter in report["chapters"]:
        if not chapter.get("exists"):
            continue
        candidates = chapter.get("follow_up_candidates") or {}
        source_candidates = candidates.get("source_chunks") or []
        answer_candidates = candidates.get("answer_cards") or []
        if not source_candidates and not answer_candidates:
            continue
        lines.append(f"### {chapter['chapter_id']}")
        for row in source_candidates[:8]:
            lines.append(
                f"- Source `{row['chunk_id']}`: {row['confidence']} / {row['word_status']} / {row['title']}"
            )
        for row in answer_candidates[:8]:
            lines.append(
                f"- Answer `{row['answer_id']}`: {row['support_type']} / {row['canonical_question']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_counts(counts: dict[str, Any]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()) if value)


def format_attention_details(details: Any) -> str:
    if not isinstance(details, dict):
        return "-"
    parts = []
    for key, value in sorted(details.items()):
        if isinstance(value, dict):
            count = value.get("count", 0)
            samples = value.get("samples") or []
            ids = [
                str(sample.get("chunk_id") or sample.get("answer_id") or "")
                for sample in samples
                if isinstance(sample, dict)
            ]
            sample_text = f" samples={','.join(ids)}" if ids else ""
            parts.append(f"{key}={count}{sample_text}")
        else:
            parts.append(f"{key}={value}")
    return "; ".join(parts) or "-"


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    raise SystemExit(main())
