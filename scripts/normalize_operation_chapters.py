from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DESKTOP_KNOWLEDGE = Path(r"C:\Users\Michael\Desktop\knowledge")
SOURCE_ASSET_ROOT = Path(r"F:\编书\道路工程数字设计方法\05脚本及图片素材")
WORD_ALIGNMENT_PATH = ROOT / "output" / "word_alignment_ch06_ch09_2026-06-04.json"

CHAPTERS = {
    "ch07": {
        "json_size": 3229218,
        "jsonl_size": 1054752,
        "title": "第7章 道路CAD软件的使用",
        "script_files": ["7.道路CAD软件使用流程.html"],
        "script_title_prefix": "道路CAD软件使用流程",
        "script_kps": ["kp_ch07_001", "kp_ch07_002", "kp_ch07_003"],
    },
    "ch08": {
        "json_size": 3105727,
        "jsonl_size": 820436,
        "title": "第8章 道路BIM软件的使用",
        "script_files": ["8.1OpenRoads Designer参数化架构.html", "8.2ORD软件功能总览与道路设计流程.html"],
        "script_title_prefix": "OpenRoads Designer互动脚本",
        "script_kps": ["kp_ch08_architecture", "kp_ch08_geometry_rules", "kp_ch08_template_logic"],
    },
    "ch09": {
        "json_size": 2394935,
        "jsonl_size": 737730,
        "title": "第9章 BIM_GIS集成方法",
        "script_files": [
            "9.1从模型驱动到数据驱动.html",
            "9.2BIM+GIS集成层次.html",
            "9.3BIM+GIS协同设计流程.html",
            "9.4Civil3D平台的道路BIM正向设计.html",
            "9.5Map3D平台的道路BIM_GIS集成.html",
            "9.6BIM_GIS在公路地质选线中的应用.html",
        ],
        "script_title_prefix": "BIM+GIS集成互动脚本",
        "script_kps": ["kp_ch09_001_bimgis_paradigm", "kp_ch09_002_model_to_data", "kp_ch09_004_integration_levels"],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize operation-oriented chapter packages.")
    parser.add_argument("--chapters", nargs="+", default=["ch07", "ch08", "ch09"], choices=sorted(CHAPTERS))
    parser.add_argument("--source-dir", type=Path, default=DESKTOP_KNOWLEDGE)
    parser.add_argument("--asset-root", type=Path, default=SOURCE_ASSET_ROOT)
    parser.add_argument("--word-alignment", type=Path, default=WORD_ALIGNMENT_PATH)
    args = parser.parse_args()

    summaries = []
    for chapter_id in args.chapters:
        summaries.append(normalize_chapter(chapter_id, args.source_dir, args.asset_root, args.word_alignment))
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


def normalize_chapter(chapter_id: str, source_dir: Path, asset_root: Path, word_alignment_path: Path) -> dict[str, Any]:
    config = CHAPTERS[chapter_id]
    source_json = find_by_size(source_dir, int(config["json_size"]), ".json")
    source_jsonl = find_by_size(source_dir, int(config["jsonl_size"]), ".jsonl")
    raw = json.loads(source_json.read_text(encoding="utf-8"))
    data = raw.get("sheets") if isinstance(raw.get("sheets"), dict) else raw
    data = {key: value for key, value in data.items()}
    if isinstance(raw.get("metadata"), dict):
        data["metadata"] = raw["metadata"]

    normalize_package(chapter_id, data, config, asset_root, word_alignment_path)

    output_dir = ROOT / "data/raw" / chapter_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / source_json.name
    output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if source_jsonl:
        shutil.copy2(source_jsonl, output_dir / source_jsonl.name)

    return {
        "chapter_id": chapter_id,
        "source_json": str(source_json),
        "source_jsonl": str(source_jsonl) if source_jsonl else None,
        "output_json": str(output_json),
        "counts": {key: len(value) if isinstance(value, list) else 1 for key, value in data.items()},
        "bound_resources": [
            row.get("resource_id")
            for row in data.get("Resources", [])
            if isinstance(row, dict) and row.get("status") == "bound"
        ],
    }


def find_by_size(source_dir: Path, size: int, suffix: str) -> Path:
    matches = [path for path in source_dir.iterdir() if path.suffix.lower() == suffix and path.stat().st_size == size]
    if not matches:
        raise SystemExit(f"Cannot find {suffix} file with size {size} under {source_dir}")
    return matches[0]


def normalize_package(chapter_id: str, data: dict[str, Any], config: dict[str, Any], asset_root: Path, word_alignment_path: Path) -> None:
    ensure_list_tables(data)
    normalize_chapter_structure(data.get("Chapter_Structure", []))
    normalize_source_chunks(data.get("Source_Chunks", []))
    normalize_knowledge_points(data.get("Knowledge_Points", []))
    normalize_answer_cards(data)
    enrich_duplicate_answer_contexts(data)
    normalize_qa_cases(data)
    normalize_rag_config(data.get("RAG_Config", []), chapter_id)
    enrich_rag_with_answer_context(data)
    normalize_embedding_corpus(data.get("Embedding_Corpus", []), chapter_id)
    normalize_resources(data, chapter_id)
    ensure_operation_media_metadata(data, chapter_id)
    normalize_relations(data, chapter_id)
    normalize_concept_comparisons(data.get("Concept_Comparison", []), chapter_id)
    data["Synonyms_Questions"] = normalize_synonyms(data.get("Synonyms", []))
    data["Question_Routing_Rules"] = normalize_routing_rules(data.get("Question_Routing_Rules", []), chapter_id)
    constraints = data.get("Answer_Guardrails") or data.get("Answer_Constraints") or data.get("Answer_Policies") or []
    data["Answer_Guardrails"] = normalize_answer_guardrails(constraints, chapter_id)
    data["Prompt_Templates"] = prompt_templates(chapter_id)
    normalize_quality_checklist(data.get("Quality_Checklist", []), chapter_id)
    bind_interactive_scripts(data, chapter_id, config, asset_root)
    add_resource_eval_cases(data, chapter_id)
    apply_word_alignment_enrichment(data, chapter_id, word_alignment_path)
    add_metadata(data, chapter_id, config)


def ensure_list_tables(data: dict[str, Any]) -> None:
    for table in [
        "Chapter_Structure",
        "Source_Chunks",
        "Knowledge_Points",
        "Answer_Cards",
        "Operation_Tasks",
        "Operation_Steps",
        "Command_Cards",
        "Software_Objects",
        "Parameter_Settings",
        "Common_Errors",
        "Video_Resources",
        "Video_Segments",
        "Screenshot_Resources",
        "Resources",
        "Resource_Relations",
        "Concept_Comparison",
        "Synonyms",
        "Knowledge_Relations",
        "Exercises",
        "QA_Testset",
        "QA_Evaluation_Testset",
        "RAG_Config",
        "Embedding_Corpus",
        "Quality_Checklist",
    ]:
        if not isinstance(data.get(table), list):
            data[table] = []


def normalize_chapter_structure(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row.setdefault("order", index)
        row["level"] = normalize_level(row.get("level"), row.get("node_type"))
        row.setdefault("learning_role", row.get("teaching_role") or row.get("learning_value") or row.get("teaching_focus") or "")


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
        repair_source_text_fragments(row)
        row["chunk_summary"] = row.get("chunk_summary") or row.get("summary") or row.get("source_excerpt") or ""
        row.setdefault("evidence_role", row.get("evidence_level") or "证据层，不作为RAG第一主检索对象")
        row.setdefault("answer_use", row.get("used_for_answer") or "用于核验答案卡与操作任务，不建议整段输出给学生")
        row["usable_for_answer"] = "no_direct_output"
        row.setdefault("review_status", row.get("status") or "checked")
        row["keywords"] = split_values(row.get("keywords"))


def repair_source_text_fragments(row: dict[str, Any]) -> None:
    changed = False
    for field in ("source_excerpt", "summary", "chunk_summary"):
        value = row.get(field)
        if not isinstance(value, str) or not value:
            continue
        repaired = normalize_source_text(value)
        if repaired != value:
            row[field] = repaired
            changed = True
    if changed:
        row["source_excerpt_text_repair_note"] = "Normalized duplicate punctuation in source excerpt fields during operation chapter rebuild."


def normalize_source_text(text: str) -> str:
    previous = None
    current = text
    while previous != current:
        previous = current
        current = current.replace("。。", "。")
        current = current.replace("．．", "。")
        current = current.replace("，，", "，")
        current = current.replace("；；", "；")
    return current


def normalize_knowledge_points(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        row["key_points"] = split_values(row.get("key_points")) or [
            value for value in [row.get("definition"), row.get("core_explanation"), row.get("engineering_meaning")] if value
        ][:3]
        row["keywords"] = split_values(row.get("keywords"))
        row["aliases"] = split_values(row.get("aliases")) or split_values(row.get("student_question_patterns"))[:4]
        row["related_kps"] = split_values(row.get("related_kps"))
        row["common_mistakes"] = split_values(row.get("common_mistakes"))
        row["source_hint"] = row.get("source_hint") or ";".join(split_values(row.get("source_chunks") or row.get("evidence_chunks")))
        row.setdefault("status", "checked")
    uniquify_id_field(rows, "kp_id", "kp")


def normalize_answer_cards(data: dict[str, Any]) -> None:
    task_by_id = {str(row.get("task_id")): row for row in data.get("Operation_Tasks", []) if isinstance(row, dict)}
    for row in data.get("Answer_Cards", []):
        if not isinstance(row, dict):
            continue
        task = task_by_id.get(str(row.get("related_task") or ""))
        context = task_context(task)
        patterns = split_values(row.get("student_question_patterns"))
        canonical = str(row.get("canonical_question") or "").strip()
        if context and canonical:
            patterns.extend([f"{context}:{canonical}", f"{context}{canonical}"])
        row["student_question_patterns"] = dedupe(patterns)
        if context:
            row["retrieval_context"] = context
        row["related_kps"] = split_values(row.get("related_kps")) or split_values(task.get("related_kps") if task else "")
        row["answer_points"] = answer_points(row)
        row["must_include"] = split_values(row.get("must_include")) or row["answer_points"][:4]
        row["avoid_content"] = split_values(row.get("avoid_content"))
        row["evidence_chunks"] = split_values(row.get("evidence_chunks") or row.get("source_chunks"))
        row["recommended_resources"] = split_values(row.get("recommended_resources"))
        if row.get("answer_mode") == "steps":
            row["answer_mode"] = "step"
        row.setdefault("status", "checked")


def enrich_duplicate_answer_contexts(data: dict[str, Any]) -> None:
    groups: dict[str, list[dict[str, Any]]] = {}
    for card in data.get("Answer_Cards", []):
        if isinstance(card, dict):
            key = compact_text(card.get("canonical_question"))
            if key:
                groups.setdefault(key, []).append(card)
    for cards in groups.values():
        if len(cards) <= 1:
            continue
        candidate_counts: dict[str, int] = {}
        for card in cards:
            for candidate in duplicate_answer_context_candidates(card):
                key = compact_text(candidate)
                candidate_counts[key] = candidate_counts.get(key, 0) + 1
        for card in cards:
            context = str(card.get("retrieval_context") or "").strip()
            if not context:
                context = next(
                    (
                        candidate
                        for candidate in duplicate_answer_context_candidates(card)
                        if candidate_counts.get(compact_text(candidate), 0) == 1
                    ),
                    "",
                )
            if not context:
                context = duplicate_answer_context(card)
            canonical = str(card.get("canonical_question") or "").strip()
            if not context or not canonical:
                continue
            card["retrieval_context"] = context
            patterns = split_values(card.get("student_question_patterns"))
            patterns.extend([canonical, f"{context}:{canonical}", f"{context}{canonical}"])
            card["student_question_patterns"] = dedupe(patterns)
            card.setdefault("canonical_question_original", canonical)
            scoped = f"{context}:{canonical}"
            if compact_text(card.get("canonical_question")) != compact_text(scoped):
                card["canonical_question"] = scoped


def duplicate_answer_context(card: dict[str, Any]) -> str:
    candidates = duplicate_answer_context_candidates(card)
    if candidates:
        return candidates[0]
    return str(card.get("answer_id") or "")


def duplicate_answer_context_candidates(card: dict[str, Any]) -> list[str]:
    result = []
    for point in split_values(card.get("answer_points")):
        text = str(point).strip()
        if not text:
            continue
        if "：" in text:
            text = text.split("：", 1)[1].strip()
        elif ":" in text:
            text = text.split(":", 1)[1].strip()
        if text and compact_text(text) != compact_text(card.get("canonical_question")):
            result.append(text[:80])
    return dedupe(result)


def answer_points(row: dict[str, Any]) -> list[str]:
    points = split_values(row.get("answer_points"))
    steps = split_values(row.get("operation_steps"))
    checks = split_values(row.get("must_check"))
    mode = str(row.get("answer_mode") or "")
    if mode == "steps" and steps:
        return dedupe([*steps, *checks])
    return dedupe([*(points or steps), *checks])


def normalize_qa_cases(data: dict[str, Any]) -> None:
    cards = [row for row in data.get("Answer_Cards", []) if isinstance(row, dict) and row.get("answer_id")]
    canonical_counts: dict[str, int] = {}
    for card in cards:
        key = compact_text(card.get("canonical_question"))
        if key:
            canonical_counts[key] = canonical_counts.get(key, 0) + 1
    cases = []
    for index, card in enumerate(cards, 1):
        question = card.get("canonical_question")
        key = compact_text(question)
        if canonical_counts.get(key, 0) > 1 and card.get("retrieval_context"):
            question = f"{card['retrieval_context']}:{question}"
        cases.append(
            {
                "test_id": f"eval_{card['answer_id']}",
                "chapter_id": card.get("chapter_id"),
                "question": question,
                "expected_answer_card": card.get("answer_id"),
                "expected_kps": card.get("related_kps") or [],
                "expected_answer_points": card.get("must_include") or card.get("answer_points") or [],
                "should_not_include": card.get("avoid_content") or [],
                "required_response_mode": card.get("answer_mode") or "bullet",
                "pass_rule": "top1_answer_and_point_coverage",
                "error_reason": "",
                "status": "checked",
            }
        )
    data["QA_Evaluation_Testset"] = cases
    data["QA_Testset"] = cases


def normalize_rag_config(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        row["object_type"] = row.get("object_type") or row.get("target_type")
        row["object_id"] = row.get("object_id") or row.get("target_id")
        row["chapter_id"] = row.get("chapter_id") or chapter_id
        row["retrieval_keywords"] = row.get("retrieval_keywords") or row.get("search_keywords") or row.get("retrieval_tags") or ""
        row["index_text"] = row.get("index_text") or row.get("embedding_text") or row.get("retrieval_keywords") or row.get("search_keywords") or ""
        row["retrieval_priority"] = priority_value(row.get("retrieval_priority"))
        row["primary_output"] = row.get("object_type") == "answer_card"


def enrich_rag_with_answer_context(data: dict[str, Any]) -> None:
    cards = {
        str(row.get("answer_id")): row
        for row in data.get("Answer_Cards", [])
        if isinstance(row, dict) and row.get("answer_id")
    }
    for row in data.get("RAG_Config", []):
        if not isinstance(row, dict) or row.get("object_type") != "answer_card":
            continue
        card = cards.get(str(row.get("object_id") or ""))
        context = str((card or {}).get("retrieval_context") or "").strip()
        if not context:
            continue
        for field in ("retrieval_keywords", "index_text"):
            current = str(row.get(field) or "")
            if context not in current:
                row[field] = f"{context};{current}" if current else context


def priority_value(value: Any) -> int:
    text = str(value or "").lower()
    if "highest" in text or "p1" in text or "high" in text or text.startswith("1_"):
        return 100
    if "medium" in text or "p2" in text:
        return 70
    if "low" in text or "p3" in text:
        return 40
    return 50


def normalize_embedding_corpus(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row["embedding_id"] = row.get("embedding_id") or row.get("corpus_id") or f"emb_{chapter_id}_{index:04d}"
        row["source_type"] = row.get("source_type") or row.get("object_type")
        row["source_id"] = row.get("source_id") or row.get("object_id")
        row["embedding_text"] = row.get("embedding_text") or row.get("text_for_embedding") or ""
        row["chapter_id"] = row.get("chapter_id") or chapter_id
    uniquify_id_field(rows, "embedding_id", "emb")


def normalize_resources(data: dict[str, Any], chapter_id: str) -> None:
    resources = data.setdefault("Resources", [])
    if not resources:
        for row in data.get("Video_Resources", []):
            if isinstance(row, dict):
                resources.append(
                    {
                        "resource_id": row.get("video_id"),
                        "chapter_id": chapter_id,
                        "section_id": row.get("section_id"),
                        "resource_type": "video",
                        "title": row.get("title"),
                        "file_path": row.get("file_path"),
                        "description": row.get("teaching_use"),
                        "related_kps": [],
                        "qa_use": row.get("qa_use"),
                        "status": row.get("status") or "placeholder",
                    }
                )
    for row in resources:
        if not isinstance(row, dict):
            continue
        row["chapter_id"] = row.get("chapter_id") or chapter_id
        row["resource_type"] = normalize_resource_type(row.get("resource_type"))
        row["related_kps"] = split_values(row.get("related_kps"))
        row["keywords"] = split_values(row.get("keywords")) or [str(row.get("title") or row.get("resource_id"))]
        row["reference_aliases"] = resource_aliases(row)
        status = str(row.get("status") or "")
        if status != "bound":
            row["status"] = "placeholder"
            row["suppress_recommendation"] = True
    for table in ("Video_Resources", "Screenshot_Resources"):
        for row in data.get(table, []):
            if isinstance(row, dict):
                row["status"] = normalize_placeholder_status(row.get("status"))


def normalize_resource_type(value: Any) -> str:
    text = str(value or "")
    if text in {"figure", "fig", "image"}:
        return "image"
    if "video" in text:
        return "video"
    return text or "resource"


def normalize_placeholder_status(value: Any) -> str:
    return "placeholder" if str(value or "").startswith("placeholder") or str(value or "").startswith("needs_") else str(value or "placeholder")


def ensure_operation_media_metadata(data: dict[str, Any], chapter_id: str) -> None:
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
    patterns = [
        (rf"{chapter_id}_vid_(\d+)_seg_\d+", f"{chapter_id}_vid_{{}}"),
        (rf"vidseg_{chapter_id}_(\d+)_\d+", f"video_{chapter_id}_{{}}"),
        (rf"{chapter_id}_vid_seg_(\d+)", None),
    ]
    for pattern, template in patterns:
        match = re.search(pattern, segment_id)
        if not match:
            continue
        number = int(match.group(1))
        if template is None:
            number = max(1, (number + 4) // 5)
            return f"{chapter_id}_vid_{number:03d}"
        return template.format(f"{number:03d}")
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


def normalize_relations(data: dict[str, Any], chapter_id: str) -> None:
    rows = data.get("Knowledge_Relations", [])
    if rows:
        for row in rows:
            if isinstance(row, dict):
                row["weight"] = row.get("weight") or row.get("relation_strength") or 1
        return
    converted = []
    for row in data.get("Resource_Relations", []):
        if not isinstance(row, dict):
            continue
        converted.append(
            {
                "relation_id": row.get("relation_id"),
                "source_id": row.get("source_id"),
                "relation_type": row.get("relation_type"),
                "target_id": row.get("target_id"),
                "weight": row.get("weight") or row.get("relation_strength") or 1,
                "description": row.get("description"),
                "use_in_recommendation": row.get("use_in_recommendation", True),
                "use_in_rag": row.get("use_in_rag", True),
                "chapter_id": chapter_id,
            }
        )
    data["Knowledge_Relations"] = converted


def normalize_concept_comparisons(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row["comparison_id"] = row.get("comparison_id") or row.get("cmp_id") or f"{chapter_id}_comp_{index:03d}"
        row["chapter_id"] = row.get("chapter_id") or chapter_id
        object_a = str(row.get("object_a") or row.get("left") or "").strip()
        object_b = str(row.get("object_b") or row.get("right") or "").strip()
        dimension = str(row.get("dimension") or row.get("comparison_dimension") or "").strip()
        if not row.get("title"):
            if object_a and object_b:
                row["title"] = f"{object_a} vs {object_b}"
            elif dimension:
                row["title"] = f"{chapter_id} concept comparison {index}: {dimension}"
            else:
                row["title"] = f"{chapter_id} concept comparison {index}"
        if not row.get("dimensions"):
            dimension_parts = [part for part in [dimension, row.get("compare_points"), row.get("key_difference")] if part]
            row["dimensions"] = split_values(dimension_parts) if dimension_parts else []
        row["answer_use"] = row.get("answer_use") or row.get("teaching_use") or row.get("qa_use") or "用于概念辨析和操作对象对比问答。"
        row["related_answer_cards"] = split_values(row.get("related_answer_cards") or row.get("related_answers"))
        row["status"] = row.get("status") or "checked"


def normalize_synonyms(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append(
            {
                **row,
                "alias_or_question": row.get("alias_or_question") or row.get("variant") or row.get("standard_term"),
                "target_id": row.get("target_id") or row.get("related_answer") or row.get("related_kp") or row.get("standard_term"),
                "type": row.get("type") or row.get("intent") or row.get("intent_hint") or "synonym",
                "priority": row.get("priority") or row.get("weight") or 1,
            }
        )
    return result


def normalize_routing_rules(rows: list[dict[str, Any]], chapter_id: str) -> list[dict[str, Any]]:
    if not rows:
        rows = [
            {"pattern": "如何/怎么/步骤/操作", "target_table": "Operation_Tasks", "answer_mode": "step", "description": "操作任务优先"},
            {"pattern": "失败/不显示/报错/结果不对", "target_table": "Common_Errors", "answer_mode": "troubleshoot", "description": "错误排查优先"},
        ]
    result = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        result.append(
            {
                **row,
                "routing_id": row.get("routing_id") or row.get("rule_id") or f"{chapter_id}_route_{index:03d}",
                "pattern": row.get("pattern") or row.get("question_pattern") or row.get("intent") or "",
                "target_table": row.get("target_table") or row.get("primary_table") or row.get("route_to") or "",
                "answer_mode": row.get("answer_mode") or row.get("answer_template") or "",
                "description": row.get("description") or row.get("rule") or "",
            }
        )
    return result


def normalize_answer_guardrails(rows: list[dict[str, Any]], chapter_id: str) -> list[dict[str, Any]]:
    if not rows:
        rows = [{"rule": "禁止把Source_Chunks作为主答案输出", "severity": "high"}]
    result = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        result.append(
            {
                **row,
                "guardrail_id": row.get("guardrail_id") or row.get("constraint_id") or row.get("policy_id") or f"{chapter_id}_guardrail_{index:03d}",
                "title": row.get("title") or row.get("rule") or f"{chapter_id}回答约束{index}",
                "rule": row.get("rule") or row.get("policy") or row.get("description") or "",
                "severity": row.get("severity") or "medium",
            }
        )
    return result


def prompt_templates(chapter_id: str) -> list[dict[str, Any]]:
    return [
        {
            "template_id": f"{chapter_id}_operation_answer_template",
            "chapter_id": chapter_id,
            "name": "操作步骤回答模板",
            "trigger": "operation_steps",
            "template": "按操作目标、前置条件、操作步骤、关键参数、结果检查、常见错误组织回答；不整段复制教材原文。",
            "status": "checked",
        },
        {
            "template_id": f"{chapter_id}_error_diagnosis_template",
            "chapter_id": chapter_id,
            "name": "错误排查回答模板",
            "trigger": "operation_error",
            "template": "按错误现象、可能原因、检查顺序、解决步骤、关联任务组织回答；视频未制作时不推荐可播放片段。",
            "status": "checked",
        },
    ]


def normalize_quality_checklist(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row["check_id"] = row.get("check_id") or f"{chapter_id}_quality_{index:03d}"
        row["item"] = row.get("item") or row.get("title") or row.get("rule") or f"{chapter_id}质量检查{index}"
        row["criterion"] = row.get("criterion") or row.get("note") or row.get("rule") or ""
        row["status"] = row.get("status") or "checked"


def bind_interactive_scripts(data: dict[str, Any], chapter_id: str, config: dict[str, Any], asset_root: Path) -> None:
    resources = data.setdefault("Resources", [])
    scripts = data.setdefault("Interactive_Scripts", [])
    asset_dir = ROOT / "assets" / chapter_id / "interactive_html"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for index, filename in enumerate(config["script_files"], 1):
        source = asset_root / filename
        if not source.exists():
            continue
        target = asset_dir / filename
        shutil.copy2(source, target)
        resource_id = f"{chapter_id}_script_{index:02d}"
        script_id = f"{chapter_id}_script_{index:02d}"
        title = Path(filename).stem
        file_path = target.relative_to(ROOT).as_posix()
        related_kps = list(config.get("script_kps") or [])
        upsert_by_id(
            resources,
            "resource_id",
            {
                "resource_id": resource_id,
                "chapter_id": chapter_id,
                "section_id": f"{chapter_id}_sec_interactive",
                "resource_type": "interactive_html",
                "title": title,
                "file_path": file_path,
                "description": f"用于浏览{config['title']}的实践流程、软件对象和典型操作任务。",
                "related_kps": related_kps,
                "keywords": [title, str(config.get("script_title_prefix")), "互动脚本", "操作流程"],
                "trigger_questions": [
                    f"{title}怎么看？",
                    f"我想看{title}。",
                    f"{config['title']}互动脚本怎么操作？",
                ],
                "teaching_use": "课堂演示、学生自学和操作任务导览。",
                "qa_use": "学生询问互动脚本、操作演示或实践流程时推荐。",
                "status": "bound",
            },
        )
        upsert_by_id(
            scripts,
            "script_id",
            {
                "script_id": script_id,
                "resource_id": resource_id,
                "chapter_id": chapter_id,
                "title": title,
                "file_path": file_path,
                "interaction_theme": title,
                "display_objects": ["实践流程", "软件对象", "操作任务", "常见错误"],
                "operation_steps": ["打开脚本", "按模块查看功能", "结合操作任务定位步骤和检查项"],
                "trigger_questions": [f"{title}怎么看？", f"我想看{title}。"],
                "related_kps": related_kps,
                "extracted_labels": [],
                "status": "bound",
            },
        )


def add_resource_eval_cases(data: dict[str, Any], chapter_id: str) -> None:
    cases = []
    for resource in data.get("Resources", []):
        if not isinstance(resource, dict) or resource.get("status") != "bound":
            continue
        if resource.get("resource_type") != "interactive_html":
            continue
        questions = split_values(resource.get("trigger_questions")) or [f"{resource.get('title')}怎么看？"]
        title = str(resource.get("title") or "")
        scoped_questions = [question for question in questions if title and title in str(question)]
        questions = scoped_questions or questions[:1]
        for index, question in enumerate(questions, 1):
            cases.append(
                {
                    "test_id": f"res_eval_{resource['resource_id']}_{index:02d}",
                    "chapter_id": chapter_id,
                    "question": question,
                    "expected_resource_id": resource.get("resource_id"),
                    "expected_resource_type": resource.get("resource_type"),
                    "expected_answer_mode": "resource_guidance",
                    "related_kps": resource.get("related_kps") or [],
                    "resource_intent": "interactive_script",
                    "pass_rule": "top1_resource_and_mode",
                }
            )
    data["Resource_Evaluation_Testset"] = cases


def apply_word_alignment_enrichment(data: dict[str, Any], chapter_id: str, word_alignment_path: Path) -> None:
    chapter = load_word_alignment_chapter(word_alignment_path, chapter_id)
    if not chapter:
        return

    source_applied = apply_source_chunk_word_alignment(data, chapter)
    answer_applied = apply_answer_card_word_alignment(data, chapter)
    data.setdefault("metadata", {})
    if isinstance(data["metadata"], dict):
        data["metadata"]["word_alignment"] = {
            "source": str(word_alignment_path),
            "word_range": chapter.get("word_range") or {},
            "source_chunk_alignment": chapter.get("source_chunk_alignment") or {},
            "knowledge_point_alignment": chapter.get("knowledge_point_alignment") or {},
            "operation_task_alignment": chapter.get("operation_task_alignment") or {},
            "answer_card_alignment": chapter.get("answer_card_alignment") or {},
            "heading_coverage": chapter.get("heading_coverage") or {},
            "source_chunks_enriched": source_applied,
            "answer_cards_enriched": answer_applied,
            "policy": "Word alignment is used as automated textbook evidence grading for stable operation chapters. Source_Chunks remain evidence-only and are not treated as verbatim textbook quotes.",
        }


def load_word_alignment_chapter(path: Path, chapter_id: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    chapters = payload.get("chapters") or []
    if isinstance(chapters, dict):
        chapters = list(chapters.values())
    for chapter in chapters:
        if isinstance(chapter, dict) and chapter.get("chapter_id") == chapter_id:
            return chapter
    return {}


def apply_source_chunk_word_alignment(data: dict[str, Any], chapter: dict[str, Any]) -> int:
    source_by_id = {
        str(row.get("chunk_id")): row
        for row in data.get("Source_Chunks", [])
        if isinstance(row, dict) and row.get("chunk_id")
    }
    applied = 0
    for item in chapter.get("source_rows") or []:
        if not isinstance(item, dict):
            continue
        chunk = source_by_id.get(str(item.get("chunk_id") or ""))
        if chunk is None:
            continue
        profile = operation_source_evidence_profile(str(item.get("status") or ""), item.get("support_terms") or [])
        chunk["word_alignment"] = {
            "status": item.get("status") or "",
            "classification": profile["classification"],
            "heading_path": item.get("heading_path") or "",
            "support_terms": item.get("support_terms") or [],
        }
        chunk["word_correspondence"] = {
            "source": "word_alignment_ch06_ch09_2026-06-04",
            "status": item.get("status") or "",
            "classification": profile["classification"],
            "excerpt_preview": item.get("excerpt_preview") or "",
            "not_verbatim_quote": True,
        }
        chunk["evidence_quality_profile"] = {
            "mode": "automated_operation_textbook_evidence_grading",
            "evidence_confidence": profile["evidence_confidence"],
            "evidence_boundary_type": profile["evidence_boundary_type"],
            "source_excerpt_role": profile["source_excerpt_role"],
            "review_status": profile["review_status"],
            "answer_use": profile["answer_use"],
            "usable_for_answer": "no_direct_output",
            "needs_textbook_anchor_review": profile["needs_textbook_anchor_review"],
            "not_verbatim_quote": True,
        }
        chunk["review_status"] = profile["review_status"]
        chunk["source_excerpt_role"] = profile["source_excerpt_role"]
        chunk["word_verification"] = profile["word_verification"]
        chunk["answer_use"] = profile["answer_use"]
        chunk["usable_for_answer"] = "no_direct_output"
        applied += 1
    return applied


def operation_source_evidence_profile(status: str, support_terms: list[Any]) -> dict[str, Any]:
    normalized = str(status or "").strip()
    has_terms = bool(support_terms)
    if normalized == "exact":
        return {
            "classification": "direct_text_evidence",
            "evidence_confidence": "high",
            "evidence_boundary_type": "direct_text_or_heading",
            "source_excerpt_role": "auto_direct_text_evidence_not_verbatim",
            "word_verification": "auto_direct_text_supported",
            "review_status": "auto_evidence_graded",
            "answer_use": "教材证据层：Word 正文或标题直接支撑，可辅助答案核验；不直接整段输出。",
            "needs_textbook_anchor_review": False,
        }
    if normalized == "partial":
        return {
            "classification": "partial_text_evidence",
            "evidence_confidence": "medium",
            "evidence_boundary_type": "partial_text_or_heading",
            "source_excerpt_role": "auto_partial_text_evidence_not_verbatim",
            "word_verification": "auto_partial_text_supported",
            "review_status": "auto_evidence_graded",
            "answer_use": "教材证据层：Word 局部内容支撑，可辅助答案核验；不作为完整原句引用。",
            "needs_textbook_anchor_review": False,
        }
    if normalized == "concept_supported":
        return {
            "classification": "concept_or_operation_anchor",
            "evidence_confidence": "medium",
            "evidence_boundary_type": "concept_supported_summary",
            "source_excerpt_role": "auto_concept_operation_anchor_not_verbatim",
            "word_verification": "auto_concept_operation_supported",
            "review_status": "auto_evidence_graded",
            "answer_use": "教材证据层：概念或操作主题在 Word 中可支撑，Source_Chunk 为教学化摘要。",
            "needs_textbook_anchor_review": False,
        }
    return {
        "classification": "operation_summary_with_term_support" if has_terms else "operation_summary_not_verbatim",
        "evidence_confidence": "low" if not has_terms else "medium",
        "evidence_boundary_type": "operation_teaching_summary",
        "source_excerpt_role": "auto_operation_summary_not_verbatim",
        "word_verification": "auto_operation_summary_not_direct_quote",
        "review_status": "auto_evidence_downgraded" if not has_terms else "auto_evidence_graded",
        "answer_use": "辅助证据：操作型结构化摘要用于支撑任务/知识点检索，不作为教材原句或RAG主回答内容。",
        "needs_textbook_anchor_review": not has_terms,
    }


def apply_answer_card_word_alignment(data: dict[str, Any], chapter: dict[str, Any]) -> int:
    cards = {
        str(row.get("answer_id")): row
        for row in data.get("Answer_Cards", [])
        if isinstance(row, dict) and row.get("answer_id")
    }
    hit_tasks = {
        str(row.get("id"))
        for row in chapter.get("operation_task_rows") or []
        if isinstance(row, dict) and row.get("word_hit")
    }
    hit_kps = {
        str(row.get("id"))
        for row in chapter.get("knowledge_point_rows") or []
        if isinstance(row, dict) and row.get("word_hit")
    }
    comparison_index = [
        {
            "comparison_id": row.get("comparison_id") or "",
            "terms": [
                str(row.get(field) or "").strip()
                for field in ("title", "object_a", "object_b")
                if str(row.get(field) or "").strip()
            ],
        }
        for row in data.get("Concept_Comparison", [])
        if isinstance(row, dict)
    ]
    applied = 0
    for item in chapter.get("answer_card_rows") or []:
        if not isinstance(item, dict):
            continue
        card = cards.get(str(item.get("answer_id") or ""))
        if card is None:
            continue
        related_task = str(card.get("related_task") or "")
        related_kps = split_values(card.get("related_kps"))
        direct_hit = bool(item.get("word_hit"))
        task_supported = related_task in hit_tasks if related_task else False
        kp_supported = any(kp in hit_kps for kp in related_kps)
        comparison_supported = answer_supported_by_comparison(card, comparison_index)
        if direct_hit:
            support_type = "direct_word_question_hit"
            confidence_value = "high"
            needs_review = False
        elif task_supported or kp_supported:
            support_type = "teaching_rewrite_supported_by_task_or_kp"
            confidence_value = "medium"
            needs_review = False
        elif comparison_supported:
            support_type = "teaching_rewrite_supported_by_concept_comparison"
            confidence_value = "medium"
            needs_review = False
        else:
            support_type = "word_direct_question_missing"
            confidence_value = "low"
            needs_review = True
        card["word_alignment"] = {
            "source": "word_alignment_ch06_ch09_2026-06-04",
            "word_hit": direct_hit,
            "matched_term": item.get("matched_term") or "",
            "support_type": support_type,
            "evidence_confidence": confidence_value,
            "related_task_word_hit": task_supported,
            "related_kp_word_hit": kp_supported,
            "concept_comparison_supported": comparison_supported,
            "needs_textbook_anchor_review": needs_review,
            "not_verbatim_quote": True,
        }
        applied += 1
    return applied


def answer_supported_by_comparison(card: dict[str, Any], comparison_index: list[dict[str, Any]]) -> bool:
    question = compact_text(card.get("canonical_question"))
    points = compact_text(" ".join(split_values(card.get("answer_points"))))
    haystack = f"{question} {points}"
    if "区别" not in str(card.get("canonical_question") or "") and "比较" not in str(card.get("canonical_question") or ""):
        return False
    for comparison in comparison_index:
        terms: list[str] = []
        for raw_term in comparison.get("terms") or []:
            terms.append(compact_text(raw_term))
            terms.extend(compact_text(part) for part in re.split(r"与|和|/|、|vs|VS", str(raw_term)) if part.strip())
        strong_terms = [term for term in terms if len(term) >= 3]
        if strong_terms and sum(1 for term in strong_terms if term in haystack) >= 2:
            return True
    return False


def add_metadata(data: dict[str, Any], chapter_id: str, config: dict[str, Any]) -> None:
    existing = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    data["metadata"] = {
        **existing,
        "chapter_id": chapter_id,
        "chapter_title": config["title"],
        "version": existing.get("version") or "v1.0操作完备版",
        "normalized_at": "2026-06-04",
        "kb_type": "operation_oriented",
        "video_status": "operation videos are placeholders unless bound later",
        "ppt_policy": "PPT files are reference-only and are not imported into the knowledge base",
        "source_policy": "Operation_Tasks, Operation_Steps, Common_Errors and Answer_Cards are primary; Source_Chunks are evidence only.",
    }


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


def task_context(task: dict[str, Any] | None) -> str:
    if not isinstance(task, dict):
        return ""
    for field in ("task_name", "title", "task_goal", "operation_goal"):
        value = str(task.get(field) or "").strip()
        if value:
            return value
    return ""


def compact_text(value: Any) -> str:
    return "".join(str(value or "").lower().split())


def uniquify_id_field(rows: list[dict[str, Any]], id_field: str, fallback_prefix: str) -> None:
    counts: dict[str, int] = {}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row_id = str(row.get(id_field) or "").strip() or f"{fallback_prefix}_{index:04d}"
        counts[row_id] = counts.get(row_id, 0) + 1
        if counts[row_id] > 1:
            row_id = f"{row_id}_dup{counts[row_id]:02d}"
        row[id_field] = row_id


def dedupe(values: Any) -> list[str]:
    result = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result


def resource_aliases(row: dict[str, Any]) -> list[str]:
    title = str(row.get("title") or "")
    resource_id = str(row.get("resource_id") or "")
    return [value for value in dict.fromkeys([title, resource_id]) if value]


def upsert_by_id(rows: list[dict[str, Any]], id_field: str, row: dict[str, Any]) -> None:
    row_id = row[id_field]
    for index, existing in enumerate(rows):
        if isinstance(existing, dict) and existing.get(id_field) == row_id:
            rows[index] = row
            return
    rows.append(row)


if __name__ == "__main__":
    raise SystemExit(main())
