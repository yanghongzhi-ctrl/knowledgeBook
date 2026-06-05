from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "output/resource_coverage_audit_2026-06-04.json"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".tif", ".tiff", ".emf"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit chapter resource coverage and asset bindings.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = {
        "scope": "ch01-ch05 resource coverage, asset availability, resource evaluation coverage, and source verification summary",
        "chapters": [audit_chapter(path) for path in sorted((ROOT / "data/raw").glob("ch*/*.json"))],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary(report), ensure_ascii=False, indent=2))
    print(f"report={args.output}")
    return 0


def audit_chapter(package_path: Path) -> dict[str, Any]:
    data = json.loads(package_path.read_text(encoding="utf-8"))
    chapter_id = package_path.parent.name
    resources = [r for r in data.get("Resources", []) if isinstance(r, dict)]
    eval_cases = [e for e in data.get("Resource_Evaluation_Testset", []) if isinstance(e, dict)]
    source_chunks = [s for s in data.get("Source_Chunks", []) if isinstance(s, dict)]

    eval_by_resource = Counter(str(e.get("expected_resource_id") or "") for e in eval_cases)
    assets_by_name = chapter_assets(chapter_id)

    resource_rows = []
    for resource in resources:
        resource_id = str(resource.get("resource_id") or "")
        file_path = str(resource.get("file_path") or "")
        status = str(resource.get("status") or "")
        resolved = resolve_asset(file_path)
        candidates = [
            path.relative_to(ROOT).as_posix()
            for path in assets_by_name.get(resource_id.lower(), [])
            if path != resolved
        ]
        row = {
            "resource_id": resource_id,
            "resource_type": resource.get("resource_type"),
            "title": resource.get("title"),
            "status": status,
            "file_path": file_path,
            "file_exists": bool(resolved and resolved.exists()),
            "eval_cases": eval_by_resource[resource_id],
            "related_kps_count": len(resource.get("related_kps") or []),
            "candidate_assets": candidates,
            "issues": [],
        }
        if "placeholder" in status.lower():
            row["issues"].append("placeholder_status")
        if file_path and not row["file_exists"]:
            row["issues"].append("missing_file")
        if not file_path and candidates:
            row["issues"].append("candidate_asset_unbound")
        if eval_by_resource[resource_id] == 0:
            row["issues"].append("no_resource_eval_case")
        if row["related_kps_count"] == 0:
            row["issues"].append("no_related_kps")
        resource_rows.append(row)

    return {
        "chapter_id": chapter_id,
        "package_path": package_path.relative_to(ROOT).as_posix(),
        "resource_count": len(resources),
        "resource_type_counts": dict(Counter(str(r.get("resource_type") or "missing") for r in resources)),
        "resource_status_counts": dict(Counter(str(r.get("status") or "missing") for r in resources)),
        "resource_eval_cases": len(eval_cases),
        "source_word_verification": dict(Counter(str(s.get("word_verification") or "missing") for s in source_chunks)),
        "problem_resources": [row for row in resource_rows if row["issues"]],
        "asset_duplicates": asset_duplicates(chapter_id),
    }


def chapter_assets(chapter_id: str) -> dict[str, list[Path]]:
    assets: dict[str, list[Path]] = {}
    base = ROOT / "assets" / chapter_id
    if not base.exists():
        return assets
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            assets.setdefault(path.stem.lower(), []).append(path)
    return assets


def resolve_asset(file_path: str) -> Path | None:
    if not file_path or file_path.startswith(("http://", "https://")):
        return None
    return ROOT / file_path


def asset_duplicates(chapter_id: str) -> list[dict[str, Any]]:
    base = ROOT / "assets" / chapter_id / "images"
    if not base.exists():
        return []
    by_hash: dict[str, list[Path]] = {}
    for path in base.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES - {".emf"}:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            by_hash.setdefault(digest, []).append(path)
    return [
        {"sha256": digest, "files": [p.relative_to(ROOT).as_posix() for p in paths]}
        for digest, paths in by_hash.items()
        if len(paths) > 1
    ]


def summary(report: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for chapter in report["chapters"]:
        issue_counts = Counter(
            issue
            for resource in chapter["problem_resources"]
            for issue in resource["issues"]
        )
        rows.append(
            {
                "chapter_id": chapter["chapter_id"],
                "resources": chapter["resource_count"],
                "statuses": chapter["resource_status_counts"],
                "resource_eval_cases": chapter["resource_eval_cases"],
                "source_word_verification": chapter["source_word_verification"],
                "issue_counts": dict(issue_counts),
                "asset_duplicates": len(chapter["asset_duplicates"]),
            }
        )
    return {"chapters": rows}


if __name__ == "__main__":
    raise SystemExit(main())
