from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from normalize_operation_chapters import WORD_ALIGNMENT_PATH, apply_word_alignment_enrichment


ROOT = Path(__file__).resolve().parents[1]
DESKTOP_KNOWLEDGE = Path(r"C:\Users\Michael\Desktop\knowledge")
DOWNLOADS = Path(r"C:\Users\Michael\Downloads")
SOURCE_ASSET_ROOT = Path(r"F:\编书\道路工程数字设计方法\05脚本及图片素材")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize the chapter 6 operation-oriented package.")
    parser.add_argument("--source-json", type=Path, default=None)
    parser.add_argument("--source-jsonl", type=Path, default=None)
    parser.add_argument("--asset-root", type=Path, default=SOURCE_ASSET_ROOT)
    parser.add_argument("--word-alignment", type=Path, default=WORD_ALIGNMENT_PATH)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/raw/ch06")
    args = parser.parse_args()

    source_json = args.source_json or find_ch06_json()
    source_jsonl = args.source_jsonl or find_ch06_jsonl()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / source_json.name.replace(" (1)", "")

    data = json.loads(source_json.read_text(encoding="utf-8"))
    normalize_package(data, args.asset_root, args.word_alignment)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if source_jsonl and source_jsonl.exists():
        archive = output_dir / source_jsonl.name
        if source_jsonl.resolve() != archive.resolve():
            shutil.copy2(source_jsonl, archive)

    summary = {
        "source_json": str(source_json),
        "source_jsonl": str(source_jsonl) if source_jsonl else None,
        "output": str(output_path),
        "counts": {
            key: len(value) if isinstance(value, list) else 1
            for key, value in data.items()
        },
        "bound_resources": [
            row.get("resource_id")
            for row in data.get("Resources", [])
            if isinstance(row, dict) and row.get("status") == "bound"
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def find_ch06_json() -> Path:
    matches = sorted(
        (
            path
            for path in DESKTOP_KNOWLEDGE.glob("*.json")
            if "AutoCAD" in path.name and "第6章" in path.name and " (1)" not in path.name
        ),
        key=lambda path: path.name,
    )
    if not matches:
        matches = sorted(
            (
                path
                for path in DESKTOP_KNOWLEDGE.glob("*.json")
                if "AutoCAD" in path.name and "第6章" in path.name
            ),
            key=lambda path: path.name,
        )
    if not matches:
        raise SystemExit("Cannot find chapter 6 AutoCAD JSON under Desktop/knowledge.")
    return matches[0]


def find_ch06_jsonl() -> Path | None:
    matches = sorted(
        (
            path
            for path in DOWNLOADS.glob("*.jsonl")
            if "第6章" in path.name or "6" in path.name
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def normalize_package(data: dict[str, Any], asset_root: Path, word_alignment_path: Path) -> None:
    data["Synonyms_Questions"] = normalize_synonyms(data.get("Synonyms", []))
    data["Question_Routing_Rules"] = normalize_routing_rules(data.get("Routing_Rules", []))
    data["Answer_Guardrails"] = normalize_answer_guardrails(data.get("Answer_Policies", []))
    data["Prompt_Templates"] = prompt_templates()

    normalize_chapter_structure(data.get("Chapter_Structure", []))
    normalize_source_chunks(data.get("Source_Chunks", []))
    normalize_knowledge_points(data.get("Knowledge_Points", []))
    normalize_answer_cards(data)
    normalize_qa_cases(data)
    normalize_rag_config(data.get("RAG_Config", []))
    normalize_embedding_corpus(data.get("Embedding_Corpus", []))
    normalize_quality_checklist(data.get("Quality_Checklist", []))
    normalize_resources(data)
    ensure_operation_media_metadata(data)
    bind_interactive_script(data, asset_root)
    add_resource_eval_cases(data)
    apply_word_alignment_enrichment(data, "ch06", word_alignment_path)
    add_metadata(data)


def normalize_chapter_structure(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row["level"] = normalize_level(row.get("level"), row.get("node_type"))
        row.setdefault("order", index)
        row.setdefault("learning_role", row.get("knowledge_role") or row.get("node_type") or "")


def normalize_level(level: Any, node_type: Any) -> str:
    text = str(node_type or level or "").lower()
    if text == "chapter" or str(level) == "1":
        return "chapter"
    if text == "section" or str(level) == "2":
        return "section"
    return str(level or text or "")


def normalize_source_chunks(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        repair_xml_source_excerpt(row)
        row.setdefault("evidence_role", "证据层，不作为RAG第一主检索对象")
        row.setdefault("answer_use", "用于核验答案卡、操作任务和命令卡的教材依据，不建议整段输出给学生")
        row["usable_for_answer"] = "no_direct_output"
        row.setdefault("review_status", row.get("status") or "checked")
        row["keywords"] = split_values(row.get("keywords"))


def repair_xml_source_excerpt(row: dict[str, Any]) -> None:
    excerpt = str(row.get("source_excerpt") or "")
    summary = str(row.get("summary") or row.get("chunk_summary") or "")
    if not has_word_xml_residue(excerpt) and not has_word_xml_residue(summary):
        return
    replacement = clean_word_xml_residue(excerpt) or clean_word_xml_residue(summary)
    if not replacement:
        replacement = "该证据片段原始稿中残留Word XML格式内容，需结合教材正文人工复核。"
    row["source_excerpt_original_xml_residue"] = excerpt[:500]
    row["source_excerpt"] = replacement
    if has_word_xml_residue(summary):
        row["summary"] = replacement
    row["source_excerpt_repair_note"] = "原source_excerpt残留Word XML格式片段，已用summary替换作为证据预览；正式引用需以Word教材正文为准。"


def has_word_xml_residue(text: str) -> bool:
    return "<w:" in text or "</w:" in text or "<w:r" in text or "</w:r" in text


def clean_word_xml_residue(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.replace("w:tab", " ").strip()
    if has_word_xml_residue(cleaned):
        return ""
    return cleaned


def normalize_knowledge_points(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        row["key_points"] = split_values(row.get("key_points")) or [
            value
            for value in [
                row.get("definition"),
                row.get("core_explanation"),
                row.get("engineering_meaning"),
            ]
            if value
        ][:3]
        row["keywords"] = split_values(row.get("keywords"))
        row["aliases"] = split_values(row.get("student_question_patterns"))[:4]
        row["related_kps"] = split_values(row.get("related_kps"))
        row["common_mistakes"] = split_values(row.get("common_mistakes"))
        row.setdefault("source_hint", ";".join(split_values(row.get("evidence_chunks"))))


def normalize_answer_cards(data: dict[str, Any]) -> None:
    task_by_id = {
        str(row.get("task_id")): row
        for row in data.get("Operation_Tasks", [])
        if isinstance(row, dict) and row.get("task_id")
    }
    for row in data.get("Answer_Cards", []):
        if not isinstance(row, dict):
            continue
        related_task = str(row.get("related_task") or "")
        task = task_by_id.get(related_task)
        row["student_question_patterns"] = split_values(row.get("student_question_patterns"))
        row["related_kps"] = split_values(row.get("related_kps")) or split_values(task.get("related_kps") if task else "")
        row["related_steps"] = split_values(row.get("related_steps"))
        row["answer_points"] = operation_answer_points(row)
        row["must_include"] = split_values(row.get("must_check")) or split_values(row.get("must_include"))
        row["avoid_content"] = split_values(row.get("avoid_content"))
        row["evidence_chunks"] = split_values(row.get("evidence_chunks"))
        row["recommended_resources"] = []
        row.setdefault("concise_answer", build_concise_answer(row, task))
        row.setdefault("expanded_answer", build_expanded_answer(row, task))
        if row.get("answer_mode") == "steps":
            row["answer_mode"] = "step"


def operation_answer_points(row: dict[str, Any]) -> list[str]:
    steps = split_values(row.get("operation_steps"))
    points = split_values(row.get("answer_points"))
    checks = split_values(row.get("must_check")) or split_values(row.get("must_include"))
    if row.get("question_type") == "operation_steps" and steps:
        return dedupe([*steps, *checks])
    return dedupe([*(points or steps), *checks])


def build_concise_answer(row: dict[str, Any], task: dict[str, Any] | None) -> str:
    if task:
        return f"{task.get('task_name')}的目标是：{task.get('task_goal')}"
    points = operation_answer_points(row)
    return "；".join(points[:3])


def build_expanded_answer(row: dict[str, Any], task: dict[str, Any] | None) -> str:
    parts = []
    if task:
        parts.append(f"操作目标：{task.get('task_goal')}")
        parts.append(f"前置条件：{task.get('prerequisite')}")
        parts.append(f"预期结果：{task.get('output_result')}")
    points = operation_answer_points(row)
    if points:
        parts.append("操作要点：" + "；".join(points))
    checks = split_values(row.get("must_check"))
    if checks:
        parts.append("结果检查：" + "；".join(checks))
    return "\n".join(parts)


def normalize_qa_cases(data: dict[str, Any]) -> None:
    cards = {
        str(row.get("answer_id")): row
        for row in data.get("Answer_Cards", [])
        if isinstance(row, dict) and row.get("answer_id")
    }
    normalized = []
    for row in data.get("QA_Evaluation_Testset", []):
        if not isinstance(row, dict):
            continue
        expected = str(row.get("expected_answer_card") or row.get("must_hit") or "")
        card = cards.get(expected, {})
        normalized.append(
            {
                **row,
                "test_id": row.get("test_id") or row.get("eval_id"),
                "expected_answer_card": expected,
                "expected_kps": split_values(card.get("related_kps")),
                "expected_answer_points": split_values(row.get("must_include")) or split_values(card.get("must_include")),
                "should_not_include": split_values(row.get("must_not_include")),
                "required_response_mode": card.get("answer_mode") or "bullet",
                "pass_rule": row.get("pass_rule") or row.get("pass_criteria") or "top1_answer_and_point_coverage",
                "error_reason": "",
            }
        )
    data["QA_Evaluation_Testset"] = normalized
    data.setdefault("QA_Testset", normalized)


def normalize_rag_config(rows: list[dict[str, Any]]) -> None:
    priority_map = {"highest": 120, "high": 100, "medium": 70, "low": 40}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row["index_text"] = row.get("index_text") or row.get("embedding_text") or row.get("retrieval_keywords") or ""
        priority = str(row.get("retrieval_priority") or "").lower()
        row["retrieval_priority"] = priority_map.get(priority, row.get("retrieval_priority") or 50)
        row["primary_output"] = row.get("object_type") == "answer_card"


def normalize_embedding_corpus(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        row["source_type"] = row.get("source_type") or row.get("object_type")
        row["source_id"] = row.get("source_id") or row.get("object_id")
        row["embedding_text"] = row.get("embedding_text") or row.get("text_for_embedding") or ""


def normalize_resources(data: dict[str, Any]) -> None:
    for row in data.get("Resources", []):
        if not isinstance(row, dict):
            continue
        if row.get("resource_type") == "figure":
            row["resource_type"] = "image"
        row["related_kps"] = split_values(row.get("related_kps"))
        row["keywords"] = split_values(row.get("keywords")) or [row.get("title")]
        row["reference_aliases"] = resource_aliases(row)
        if row.get("status") == "placeholder":
            row["file_path"] = str(row.get("file_path") or "")
            row["suppress_recommendation"] = True

    for table, id_field in (("Video_Resources", "video_id"), ("Screenshot_Resources", "screenshot_id")):
        for row in data.get(table, []):
            if not isinstance(row, dict):
                continue
            row["related_kps"] = split_values(row.get("related_kps"))
            row["reference_aliases"] = resource_aliases(row, id_field=id_field)


def ensure_operation_media_metadata(data: dict[str, Any]) -> None:
    chapter_id = "ch06"
    videos = data.setdefault("Video_Resources", [])
    segments = data.setdefault("Video_Segments", [])
    screenshots = data.setdefault("Screenshot_Resources", [])
    video_by_id = {str(row.get("video_id")): row for row in videos if isinstance(row, dict) and row.get("video_id")}
    segment_by_id = {
        str(row.get("segment_id") or row.get("video_segment_id")): row
        for row in segments
        if isinstance(row, dict) and (row.get("segment_id") or row.get("video_segment_id"))
    }
    screenshot_by_id = {
        str(row.get("screenshot_id")): row
        for row in screenshots
        if isinstance(row, dict) and row.get("screenshot_id")
    }
    task_by_id = {
        str(row.get("task_id")): row
        for row in data.get("Operation_Tasks", [])
        if isinstance(row, dict) and row.get("task_id")
    }
    for step in data.get("Operation_Steps", []):
        if not isinstance(step, dict):
            continue
        task_id = str(step.get("task_id") or "")
        step_id = str(step.get("step_id") or "")
        task = task_by_id.get(task_id, {})
        video_segment_id = str(step.get("video_segment_id") or "").strip()
        if video_segment_id and video_segment_id not in segment_by_id:
            video_id = infer_video_id(chapter_id, video_segment_id)
            if video_id not in video_by_id:
                video = placeholder_video_resource(chapter_id, video_id, task)
                videos.append(video)
                video_by_id[video_id] = video
            segment = placeholder_video_segment(video_segment_id, video_id, task_id, step_id, step)
            segments.append(segment)
            segment_by_id[video_segment_id] = segment
        screenshot_id = str(step.get("screenshot_id") or "").strip()
        if screenshot_id and screenshot_id not in screenshot_by_id:
            screenshot = placeholder_screenshot(chapter_id, screenshot_id, task_id, step_id, task, step)
            screenshots.append(screenshot)
            screenshot_by_id[screenshot_id] = screenshot


def infer_video_id(chapter_id: str, segment_id: str) -> str:
    match = re.search(rf"{chapter_id}_vid_(\d+)_seg_\d+", segment_id)
    if match:
        return f"{chapter_id}_vid_{int(match.group(1)):03d}"
    return f"{chapter_id}_vid_unassigned"


def placeholder_video_resource(chapter_id: str, video_id: str, task: dict[str, Any]) -> dict[str, Any]:
    chapter_num = chapter_id.removeprefix("ch")
    return {
        "video_id": video_id,
        "chapter_id": chapter_id,
        "title": f"{task.get('task_name') or video_id}操作视频占位",
        "file_path": f"chapter_{chapter_num}/videos/{video_id}.mp4",
        "teaching_use": "由操作步骤引用自动补齐，等待正式视频文件和片段标注。",
        "status": "placeholder_metadata",
    }


def placeholder_video_segment(
    segment_id: str,
    video_id: str,
    task_id: str,
    step_id: str,
    step: dict[str, Any],
) -> dict[str, Any]:
    return {
        "segment_id": segment_id,
        "video_id": video_id,
        "title": f"{step.get('step_title') or step_id}视频片段占位",
        "start_time": "待标注",
        "end_time": "待标注",
        "related_task": task_id,
        "related_step": step_id,
        "status": "placeholder_metadata",
    }


def placeholder_screenshot(
    chapter_id: str,
    screenshot_id: str,
    task_id: str,
    step_id: str,
    task: dict[str, Any],
    step: dict[str, Any],
) -> dict[str, Any]:
    chapter_num = chapter_id.removeprefix("ch")
    return {
        "screenshot_id": screenshot_id,
        "chapter_id": chapter_id,
        "task_id": task_id,
        "step_id": step_id,
        "title": f"{task.get('task_name') or task_id}-{step.get('step_title') or step_id}截图占位",
        "file_path": f"chapter_{chapter_num}/screenshots/{screenshot_id}.png",
        "status": "placeholder_metadata",
    }


def bind_interactive_script(data: dict[str, Any], asset_root: Path) -> None:
    source = asset_root / "6.AutoCAD功能全景互动脚本.html"
    asset_dir = ROOT / "assets/ch06/interactive_html"
    asset_dir.mkdir(parents=True, exist_ok=True)
    scripts = data.setdefault("Interactive_Scripts", [])
    resources = data.setdefault("Resources", [])
    if not source.exists():
        return

    target = asset_dir / source.name
    shutil.copy2(source, target)
    file_path = target.relative_to(ROOT).as_posix()
    resource_id = "ch06_script_autocad_overview"
    script_id = "ch06_script_6_overview"
    related_kps = ["kp_ch06_001", "kp_ch06_002", "kp_ch06_005", "kp_ch06_006"]

    upsert_by_id(
        resources,
        "resource_id",
        {
            "resource_id": resource_id,
            "chapter_id": "ch06",
            "section_id": "ch06_sec01",
            "resource_type": "interactive_html",
            "title": "AutoCAD功能全景互动脚本",
            "file_path": file_path,
            "description": "用于浏览第六章AutoCAD平台功能、绘图环境、命令体系和典型操作任务。",
            "related_kps": related_kps,
            "keywords": ["AutoCAD", "功能全景", "互动脚本", "命令", "操作任务"],
            "trigger_questions": [
                "AutoCAD功能全景互动脚本怎么看？",
                "我想看第六章AutoCAD互动脚本。",
                "AutoCAD平台功能怎么操作演示？",
            ],
            "teaching_use": "课堂演示、学生自学和操作任务导览。",
            "qa_use": "学生询问第六章AutoCAD功能总览、互动脚本或操作演示时推荐。",
            "status": "bound",
        },
    )
    upsert_by_id(
        scripts,
        "script_id",
        {
            "script_id": script_id,
            "resource_id": resource_id,
            "chapter_id": "ch06",
            "title": "AutoCAD功能全景互动脚本",
            "file_path": file_path,
            "interaction_theme": "AutoCAD平台功能与操作任务导览",
            "display_objects": ["绘图环境", "命令体系", "绘图编辑", "图层图块", "标注输出", "三维建模"],
            "operation_steps": ["打开脚本", "按模块查看AutoCAD功能", "结合操作任务定位命令和检查项"],
            "trigger_questions": [
                "AutoCAD功能全景互动脚本怎么看？",
                "第六章互动脚本怎么操作？",
                "我想看AutoCAD平台功能演示。",
            ],
            "related_kps": related_kps,
            "extracted_labels": [],
            "status": "bound",
        },
    )


def add_resource_eval_cases(data: dict[str, Any]) -> None:
    cases = []
    seen = set()
    for resource in data.get("Resources", []):
        if not isinstance(resource, dict) or resource.get("status") != "bound":
            continue
        resource_id = str(resource.get("resource_id") or "")
        resource_type = str(resource.get("resource_type") or "")
        if resource_type != "interactive_html":
            continue
        questions = split_values(resource.get("trigger_questions")) or [
            f"{resource.get('title')}怎么看？",
            f"我想看{resource.get('title')}。",
        ]
        for index, question in enumerate(questions, 1):
            key = (resource_id, question)
            if key in seen:
                continue
            seen.add(key)
            cases.append(
                {
                    "test_id": f"res_eval_{resource_id}_{index:02d}",
                    "chapter_id": "ch06",
                    "question": question,
                    "expected_resource_id": resource_id,
                    "expected_resource_type": resource_type,
                    "expected_answer_mode": "resource_guidance",
                    "related_kps": resource.get("related_kps") or [],
                    "resource_intent": "interactive_script",
                    "pass_rule": "top1_resource_and_mode",
                }
            )
    data["Resource_Evaluation_Testset"] = cases


def add_metadata(data: dict[str, Any]) -> None:
    existing = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    data["metadata"] = {
        **existing,
        "chapter_id": "ch06",
        "chapter_title": "第6章 AutoCAD平台功能与使用方法",
        "version": "v1.0操作完备版",
        "normalized_at": "2026-06-04",
        "kb_type": "operation_oriented",
        "video_status": "operation videos are placeholders and will be added later",
        "ppt_policy": "PPT files are reference-only and are not imported into the knowledge base",
        "source_policy": "Operation_Tasks, Operation_Steps, Command_Cards, Common_Errors and Answer_Cards are primary; Source_Chunks are evidence only.",
    }


def normalize_synonyms(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                **row,
                "alias_or_question": row.get("alias_or_question") or row.get("variant") or row.get("standard_term"),
                "target_id": row.get("target_id") or row.get("related_answer") or row.get("related_kp") or row.get("standard_term"),
                "type": row.get("type") or row.get("intent_hint") or "synonym",
                "priority": row.get("priority") or 1,
            }
        )
    return normalized


def normalize_routing_rules(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        result.append(
            {
                **row,
                "routing_id": row.get("routing_id") or row.get("rule_id") or f"ch06_route_{index:03d}",
                "pattern": row.get("pattern") or row.get("trigger") or row.get("intent") or "",
                "target_table": row.get("target_table") or row.get("route_to") or "",
                "answer_mode": row.get("answer_mode") or row.get("response_mode") or "",
                "description": row.get("description") or row.get("rule") or "",
            }
        )
    return result


def normalize_answer_guardrails(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        result.append(
            {
                **row,
                "guardrail_id": row.get("guardrail_id") or row.get("policy_id") or f"ch06_guardrail_{index:03d}",
                "title": row.get("title") or row.get("policy_name") or f"第六章回答约束{index}",
                "rule": row.get("rule") or row.get("policy") or row.get("description") or "",
                "severity": row.get("severity") or "medium",
            }
        )
    return result


def prompt_templates() -> list[dict[str, Any]]:
    return [
        {
            "template_id": "ch06_operation_answer_template",
            "chapter_id": "ch06",
            "name": "第六章操作步骤回答模板",
            "trigger": "operation_steps",
            "template": "按操作目标、前置条件、操作步骤、关键参数、结果检查、常见错误组织回答；不整段复制教材原文。",
            "status": "checked",
        },
        {
            "template_id": "ch06_error_diagnosis_template",
            "chapter_id": "ch06",
            "name": "第六章错误排查回答模板",
            "trigger": "operation_error",
            "template": "按错误现象、可能原因、检查顺序、解决步骤、关联任务组织回答；视频未制作时不推荐可播放片段。",
            "status": "checked",
        },
    ]


def normalize_quality_checklist(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row["check_id"] = row.get("check_id") or row.get("item_id") or f"ch06_quality_{index:03d}"
        row["item"] = row.get("item") or row.get("title") or row.get("check_item") or row.get("rule") or f"第六章质量检查{index}"
        row["criterion"] = row.get("criterion") or row.get("rule") or row.get("description") or ""
        row["status"] = row.get("status") or "checked"


def resource_aliases(row: dict[str, Any], id_field: str = "resource_id") -> list[str]:
    title = str(row.get("title") or "")
    resource_id = str(row.get(id_field) or row.get("resource_id") or "")
    aliases = [title, resource_id]
    for marker in ("图6-", "表6-", "公式6-"):
        if marker in title:
            start = title.find(marker)
            label = title[start:].split()[0]
            aliases.extend([label, label.replace("-", "."), label.replace("-", "")])
    return [value for value in dict.fromkeys(aliases) if value]


def split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(split_values(item))
        return dedupe(result)
    if isinstance(value, dict):
        return [json.dumps(value, ensure_ascii=False)]
    text = str(value).strip()
    if not text:
        return []
    for sep in ["；", ";", "\n"]:
        text = text.replace(sep, "|")
    return dedupe(part.strip() for part in text.split("|") if part.strip())


def dedupe(values: Any) -> list[str]:
    result = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result


def upsert_by_id(rows: list[dict[str, Any]], id_field: str, row: dict[str, Any]) -> None:
    row_id = row[id_field]
    for index, existing in enumerate(rows):
        if isinstance(existing, dict) and existing.get(id_field) == row_id:
            rows[index] = row
            return
    rows.append(row)


if __name__ == "__main__":
    raise SystemExit(main())
