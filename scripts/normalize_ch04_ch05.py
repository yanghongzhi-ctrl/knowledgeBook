from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import normalize_ch02_ch03 as base


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(r"F:\编书\道路工程数字设计方法\05脚本及图片素材")

CHAPTERS = {
    "ch04": {
        "raw": next((ROOT / "data/raw/ch04").glob("*.json")),
        "patterns": ["4.*.html"],
    },
    "ch05": {
        "raw": next((ROOT / "data/raw/ch05").glob("*.json")),
        "patterns": ["5.*.html"],
    },
}

TABLE_MAP = {
    "question_routing": "Question_Routing_Rules",
    "answer_guardrails": "Answer_Guardrails",
}

ARRAY_SCHEMAS = {
    "chapter_structure": [
        "node_id",
        "parent_id",
        "order",
        "title",
        "level",
        "knowledge_focus",
    ],
    "source_chunks": [
        "chunk_id",
        "chapter_id",
        "section_id",
        "section_title",
        "chunk_summary",
        "source_excerpt",
        "content_type",
        "source_hint",
        "answer_use",
    ],
    "concept_comparison": [
        "concept_a",
        "concept_b",
        "dimension",
        "comparison",
        "engineering_application",
    ],
    "synonyms": [
        "synonym_id",
        "target_id",
        "standard_term",
        "alias_or_question",
        "type",
        "section_id",
    ],
    "knowledge_relations": [
        "relation_id",
        "source_id",
        "relation_type",
        "target_id",
        "weight",
        "description",
    ],
    "resources": [
        "resource_id",
        "chapter_id",
        "section_id",
        "resource_type",
        "title",
        "file_path",
        "description",
        "related_kps",
        "qa_use",
        "status",
    ],
    "exercises": [
        "exercise_id",
        "chapter_id",
        "section_id",
        "question",
        "exercise_type",
        "difficulty",
        "related_kps",
        "standard_answer_points",
        "scoring_rule",
        "status",
    ],
    "qa_testset": [
        "test_id",
        "question",
        "expected_answer_card",
        "expected_kps",
        "target_table",
        "confidence",
        "pass_rule",
    ],
    "qa_evaluation_testset": [
        "test_id",
        "question",
        "expected_answer_card",
        "expected_answer_points",
        "expected_kps",
        "should_not_include",
        "status",
        "required_response_mode",
    ],
    "rag_config": [
        "config_id",
        "object_type",
        "object_id",
        "chapter_id",
        "section_id",
        "retrieval_priority",
        "source_table",
        "answer_mode",
        "use_in_rag",
        "source_chunk_policy",
        "retrieval_keywords",
        "avoid_content",
        "notes",
    ],
    "embedding_corpus": [
        "embedding_id",
        "object_type",
        "object_id",
        "chapter_id",
        "section_id",
        "index_text",
    ],
    "question_routing": [
        "routing_id",
        "pattern",
        "target_table",
        "answer_mode",
        "description",
    ],
    "answer_guardrails": [
        "guardrail_id",
        "title",
        "rule",
        "severity",
    ],
    "quality_checklist": [
        "check_id",
        "title",
        "rule",
        "status",
    ],
}


def main() -> int:
    base.SOURCE_ROOT = SOURCE_ROOT
    base.TABLE_MAP.update(TABLE_MAP)
    for chapter_id, config in CHAPTERS.items():
        normalize_chapter(chapter_id, config)
    return 0


def normalize_chapter(chapter_id: str, config: dict[str, Any]) -> None:
    path = Path(config["raw"])
    data = json.loads(path.read_text(encoding="utf-8"))
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else None
    _convert_array_tables(data)
    normalized = base._normalize_tables(data)
    if metadata is not None:
        normalized["metadata"] = metadata
    _normalize_special_resources(normalized)
    base._normalize_rows(normalized, chapter_id)
    _ensure_comparison_ids(normalized, chapter_id)
    _ensure_quality_checklist_fields(normalized)
    base._prefer_complete_qa_testset(normalized)
    base._align_qa_modes_with_cards(normalized)
    base._copy_interactive_scripts(normalized, chapter_id, config["patterns"])
    _bind_interactive_resources(normalized)
    base._ensure_prompts(normalized, chapter_id)
    base._ensure_required_tables(normalized)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"{chapter_id}: answers={len(normalized['Answer_Cards'])} "
        f"qa={len(normalized['QA_Evaluation_Testset'])} "
        f"resources={len(normalized['Resources'])} "
        f"scripts={len(normalized['Interactive_Scripts'])}"
    )


def _convert_array_tables(data: dict[str, Any]) -> None:
    for table, schema in ARRAY_SCHEMAS.items():
        rows = data.get(table)
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], list):
            continue
        converted = []
        for row in rows:
            if not isinstance(row, list):
                converted.append(row)
                continue
            converted.append({field: row[index] if index < len(row) else "" for index, field in enumerate(schema)})
        data[table] = converted


def _ensure_quality_checklist_fields(data: dict[str, Any]) -> None:
    for row in data.get("Quality_Checklist", []):
        if not isinstance(row, dict):
            continue
        row["item"] = row.get("item") or row.get("title") or row.get("rule") or ""
        row["criterion"] = row.get("criterion") or row.get("rule") or ""


def _normalize_special_resources(data: dict[str, Any]) -> None:
    rows = data.get("Resources") or data.get("resources") or []
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        resource_type = str(row.get("resource_type") or "")
        title = str(row.get("title") or "")
        if resource_type == "figure/table":
            row["resource_type"] = "table" if title.startswith("表") else "image"
        label_match = re.search(r"(图|表|公式)\s*(\d+)[-—.](\d+)", title)
        if label_match:
            prefix, chapter, number = label_match.groups()
            row["reference_aliases"] = [
                f"{prefix}{chapter}-{number}",
                f"{prefix}{chapter}.{number}",
                f"{prefix} {chapter}-{number}",
            ]
        if row.get("file_path") in ("待绑定", "待绑定原始资源"):
            row["file_path"] = ""
        if row.get("related_kps") in ("待人工绑定", "待绑定"):
            row["related_kps"] = []
        if str(row.get("status") or "").startswith("待"):
            row["status"] = "placeholder"


def _bind_interactive_resources(data: dict[str, Any]) -> None:
    resources = [
        row
        for row in data.get("Resources", [])
        if isinstance(row, dict) and row.get("resource_type") == "interactive_html"
    ]
    if not resources:
        return
    for card in data.get("Answer_Cards", []):
        if not isinstance(card, dict):
            continue
        card_kps = set(base._as_list(card.get("related_kps")))
        if not card_kps:
            continue
        recommended = base._as_list(card.get("recommended_resources"))
        for resource in resources:
            resource_kps = set(base._as_list(resource.get("related_kps")))
            resource_id = str(resource.get("resource_id") or "")
            if resource_id and card_kps.intersection(resource_kps) and resource_id not in recommended:
                recommended.append(resource_id)
        card["recommended_resources"] = recommended


def _ensure_comparison_ids(data: dict[str, Any], chapter_id: str) -> None:
    for index, row in enumerate(data.get("Concept_Comparison", []), 1):
        if not isinstance(row, dict):
            continue
        row.setdefault("comparison_id", f"cmp_{chapter_id}_{index:03d}")
        concept_a = str(row.get("concept_a") or row.get("object_a") or "").strip()
        concept_b = str(row.get("concept_b") or row.get("object_b") or "").strip()
        if not row.get("title") and (concept_a or concept_b):
            row["title"] = f"{concept_a}与{concept_b}的比较".strip("与的比较")
        if not row.get("dimensions") and row.get("dimension"):
            row["dimensions"] = [row.get("dimension")]
        row.setdefault("answer_use", "比较辨析类问题优先检索")
        row.setdefault("status", "checked")


if __name__ == "__main__":
    raise SystemExit(main())
