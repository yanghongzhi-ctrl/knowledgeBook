from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "output" / "operation_media_intake_template_ch06_ch09_2026-06-04.csv"
CHAPTERS = ["ch06", "ch07", "ch08", "ch09"]


FIELDS = [
    "chapter_id",
    "section_id",
    "software",
    "task_id",
    "task_name",
    "task_goal",
    "step_id",
    "step_index",
    "step_title",
    "instruction",
    "expected_result",
    "check_method",
    "video_id",
    "video_title",
    "video_file_path_current",
    "video_file_path_final",
    "segment_id",
    "segment_title",
    "start_time_final",
    "end_time_final",
    "transcript_text_final",
    "keyframe_path_current",
    "keyframe_path_final",
    "screenshot_id",
    "screenshot_title",
    "screenshot_path_current",
    "screenshot_path_final",
    "screenshot_description_final",
    "asset_status",
    "reviewer",
    "review_note",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a chapter 6-9 operation media intake template.")
    parser.add_argument("--chapters", nargs="+", default=CHAPTERS, choices=CHAPTERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    chapter_summaries = []
    for chapter_id in args.chapters:
        package = load_package(chapter_id)
        chapter_rows = build_rows(chapter_id, package)
        rows.extend(chapter_rows)
        chapter_summaries.append({"chapter_id": chapter_id, "rows": len(chapter_rows)})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    json_output = args.output.with_suffix(".json")
    json_output.write_text(
        json.dumps(
            {
                "csv": str(args.output),
                "chapters": chapter_summaries,
                "rows": rows,
                "usage": "补充 video_file_path_final、start_time_final、end_time_final、transcript_text_final、keyframe_path_final、screenshot_path_final 后，可作为正式媒体回填依据。",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"csv": str(args.output), "json": str(json_output), "chapters": chapter_summaries, "rows": len(rows)}, ensure_ascii=False, indent=2))
    return 0


def load_package(chapter_id: str) -> dict[str, Any]:
    path = next((ROOT / "data/raw" / chapter_id).glob("*知识库*.json"))
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_rows(chapter_id: str, package: dict[str, Any]) -> list[dict[str, str]]:
    tasks = {str(row.get("task_id")): row for row in package.get("Operation_Tasks", []) if isinstance(row, dict)}
    videos = {str(row.get("video_id")): row for row in package.get("Video_Resources", []) if isinstance(row, dict)}
    segments = {str(row.get("segment_id")): row for row in package.get("Video_Segments", []) if isinstance(row, dict)}
    screenshots = {str(row.get("screenshot_id")): row for row in package.get("Screenshot_Resources", []) if isinstance(row, dict)}

    rows = []
    for step in package.get("Operation_Steps", []):
        if not isinstance(step, dict):
            continue
        task = tasks.get(str(step.get("task_id") or ""), {})
        segment = segments.get(str(step.get("video_segment_id") or ""), {})
        video = videos.get(str(segment.get("video_id") or ""), {})
        screenshot = screenshots.get(str(step.get("screenshot_id") or ""), {})
        rows.append(row_for_step(chapter_id, task, step, video, segment, screenshot))
    return rows


def row_for_step(
    chapter_id: str,
    task: dict[str, Any],
    step: dict[str, Any],
    video: dict[str, Any],
    segment: dict[str, Any],
    screenshot: dict[str, Any],
) -> dict[str, str]:
    video_id = text(video.get("video_id")) or infer_video_id(chapter_id, text(segment.get("segment_id")))
    segment_id = text(segment.get("segment_id")) or text(step.get("video_segment_id"))
    screenshot_id = text(screenshot.get("screenshot_id")) or text(step.get("screenshot_id"))
    return {
        "chapter_id": chapter_id,
        "section_id": text(task.get("section_id") or video.get("section_id")),
        "software": text(task.get("software") or video.get("software")),
        "task_id": text(task.get("task_id") or step.get("task_id")),
        "task_name": text(task.get("task_name")),
        "task_goal": text(task.get("task_goal")),
        "step_id": text(step.get("step_id")),
        "step_index": text(step.get("step_index")),
        "step_title": text(step.get("step_title")),
        "instruction": text(step.get("instruction")),
        "expected_result": text(step.get("expected_result")),
        "check_method": text(step.get("check_method")),
        "video_id": video_id,
        "video_title": text(video.get("title")),
        "video_file_path_current": text(video.get("file_path")),
        "video_file_path_final": text(video.get("file_path")),
        "segment_id": segment_id,
        "segment_title": text(segment.get("segment_title") or step.get("step_title")),
        "start_time_final": final_time(segment.get("start_time")),
        "end_time_final": final_time(segment.get("end_time")),
        "transcript_text_final": "" if is_placeholder(segment.get("transcript_text")) else text(segment.get("transcript_text")),
        "keyframe_path_current": text(segment.get("keyframe_path")),
        "keyframe_path_final": text(segment.get("keyframe_path")) or f"chapter_{chapter_id[-2:]}/videos/keyframes/{segment_id}.png",
        "screenshot_id": screenshot_id,
        "screenshot_title": text(screenshot.get("title") or step.get("step_title")),
        "screenshot_path_current": text(screenshot.get("file_path")),
        "screenshot_path_final": text(screenshot.get("file_path")) or f"chapter_{chapter_id[-2:]}/screenshots/{screenshot_id}.png",
        "screenshot_description_final": text(screenshot.get("description")),
        "asset_status": "pending_real_media",
        "reviewer": "",
        "review_note": "",
    }


def infer_video_id(chapter_id: str, segment_id: str) -> str:
    if "_seg_" in segment_id:
        return segment_id.split("_seg_", 1)[0]
    return f"{chapter_id}_vid_unassigned"


def final_time(value: Any) -> str:
    value_text = text(value)
    if not value_text or "待" in value_text:
        return ""
    return value_text


def is_placeholder(value: Any) -> bool:
    value_text = text(value)
    return not value_text or "待" in value_text or "占位" in value_text


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(text(item) for item in value if text(item))
    return str(value).replace("\r", " ").replace("\n", " ").strip()


if __name__ == "__main__":
    raise SystemExit(main())
