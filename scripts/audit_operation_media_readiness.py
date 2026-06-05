from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHAPTERS = ("ch06", "ch07", "ch08", "ch09")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit operation chapter video segment and screenshot readiness.")
    parser.add_argument("--chapters", nargs="+", default=list(DEFAULT_CHAPTERS))
    parser.add_argument("--out", default=str(ROOT / "output/operation_media_readiness_2026-06-04.json"))
    args = parser.parse_args()

    report = {
        "chapters": [audit_chapter(chapter_id) for chapter_id in args.chapters],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"report={out}")
    return 0


def audit_chapter(chapter_id: str) -> dict[str, Any]:
    package_path = next((ROOT / "data/raw" / chapter_id).glob("*.json"), None)
    if not package_path:
        raise SystemExit(f"No package JSON found for {chapter_id}")
    data = json.loads(package_path.read_text(encoding="utf-8"))
    video_by_id = {
        str(row.get("video_id")): row
        for row in data.get("Video_Resources", [])
        if isinstance(row, dict) and row.get("video_id")
    }
    segments = [row for row in data.get("Video_Segments", []) if isinstance(row, dict)]
    screenshots = [row for row in data.get("Screenshot_Resources", []) if isinstance(row, dict)]
    step_video_ids = {
        str(row.get("video_segment_id") or "")
        for row in data.get("Operation_Steps", [])
        if isinstance(row, dict) and row.get("video_segment_id")
    }
    step_screenshot_ids = {
        str(row.get("screenshot_id") or "")
        for row in data.get("Operation_Steps", [])
        if isinstance(row, dict) and row.get("screenshot_id")
    }
    segment_by_id = {
        str(row.get("segment_id") or row.get("video_segment_id")): row
        for row in segments
        if row.get("segment_id") or row.get("video_segment_id")
    }
    screenshot_by_id = {
        str(row.get("screenshot_id")): row
        for row in screenshots
        if row.get("screenshot_id")
    }
    segment_status = [media_status(segment, video_by_id.get(str(segment.get("video_id") or ""))) for segment in segments]
    screenshot_status = [media_status(row, None) for row in screenshots]
    missing_segment_metadata = sorted(item for item in step_video_ids if item not in segment_by_id)
    missing_screenshot_metadata = sorted(item for item in step_screenshot_ids if item not in screenshot_by_id)
    return {
        "chapter_id": chapter_id,
        "package": str(package_path),
        "video_resources": len(video_by_id),
        "video_segments": len(segments),
        "available_video_segments": sum(1 for item in segment_status if item["available"]),
        "placeholder_video_segments": sum(1 for item in segment_status if item["placeholder"]),
        "missing_video_files": sum(1 for item in segment_status if item["file_path"] and not item["exists"]),
        "screenshots": len(screenshots),
        "available_screenshots": sum(1 for item in screenshot_status if item["available"]),
        "placeholder_screenshots": sum(1 for item in screenshot_status if item["placeholder"]),
        "missing_screenshot_files": sum(1 for item in screenshot_status if item["file_path"] and not item["exists"]),
        "operation_step_video_refs": len(step_video_ids),
        "operation_step_screenshot_refs": len(step_screenshot_ids),
        "missing_segment_metadata": missing_segment_metadata[:20],
        "missing_screenshot_metadata": missing_screenshot_metadata[:20],
    }


def media_status(row: dict[str, Any], parent: dict[str, Any] | None) -> dict[str, Any]:
    file_path = str((parent or {}).get("file_path") or row.get("file_path") or "")
    path = Path(file_path)
    if file_path and not path.is_absolute():
        path = ROOT / file_path
    status = str(row.get("status") or (parent or {}).get("status") or "")
    placeholder = is_placeholder(status) or is_placeholder(str((parent or {}).get("status") or ""))
    exists = bool(file_path) and path.exists()
    return {
        "file_path": file_path,
        "exists": exists,
        "placeholder": placeholder,
        "available": exists and not placeholder,
    }


def is_placeholder(status: str) -> bool:
    text = str(status or "").strip().lower()
    return (
        not text
        or text.startswith("placeholder")
        or text.startswith("needs_")
        or "待" in text
        or "placeholder" in text
    )


if __name__ == "__main__":
    raise SystemExit(main())
