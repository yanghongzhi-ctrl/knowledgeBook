from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from .loader import KnowledgePackage


VERSION_ID = "ch01_kb_v1.0"
CHAPTER_ID = "ch01"
VERSION = "v1.0"


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def jsonb_literal(value: Any) -> str:
    return sql_literal(json.dumps(value if value is not None else {}, ensure_ascii=False)) + "::jsonb"


def bool_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if str(value).lower() in {"true", "1", "yes"}:
        return "TRUE"
    return "FALSE"


def write_seed_sql(package: KnowledgePackage, output_path: str | Path, status: str = "draft") -> Path:
    global VERSION_ID, CHAPTER_ID, VERSION

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256(package.path.read_bytes()).hexdigest()
    CHAPTER_ID = _infer_chapter_id(package)
    VERSION_ID = f"{CHAPTER_ID}_kb_v1.0"
    VERSION = _infer_version(package)
    chapter_title = _infer_chapter_title(package)

    lines = [
        f"-- Generated from {CHAPTER_ID} knowledge package.",
        "BEGIN;",
        "",
        "INSERT INTO kb_chapters (chapter_id, title, current_version)",
        f"VALUES ({sql_literal(CHAPTER_ID)}, {sql_literal(chapter_title)}, {sql_literal(VERSION_ID)})",
        "ON CONFLICT (chapter_id) DO UPDATE SET title = EXCLUDED.title, current_version = EXCLUDED.current_version, updated_at = now();",
        "",
        "INSERT INTO kb_versions (version_id, chapter_id, version, build_date, source_file, source_checksum, status, raw_metadata)",
        (
            f"VALUES ({sql_literal(VERSION_ID)}, {sql_literal(CHAPTER_ID)}, {sql_literal(VERSION)}, "
            f"{sql_literal(date.today().isoformat())}, {sql_literal(str(package.path))}, {sql_literal(checksum)}, "
            f"{sql_literal(status)}, {jsonb_literal(package.data.get('README', []))})"
        ),
        "ON CONFLICT (version_id) DO UPDATE SET "
        "build_date = EXCLUDED.build_date, source_file = EXCLUDED.source_file, "
        "source_checksum = EXCLUDED.source_checksum, status = EXCLUDED.status, raw_metadata = EXCLUDED.raw_metadata;",
        "",
        "-- Replace the complete version snapshot so removed objects do not remain in PostgreSQL.",
        f"DELETE FROM rag_eval_cases WHERE run_id IN (SELECT run_id FROM rag_eval_runs WHERE version_id = {sql_literal(VERSION_ID)});",
        f"DELETE FROM rag_eval_runs WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM resource_evaluation_testset WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM interactive_scripts WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM rag_config WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM embedding_corpus WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM synonym_questions WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM knowledge_relations WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM concept_comparisons WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM exercises WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM qa_evaluation_testset WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM source_chunks WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM answer_cards WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM knowledge_points WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM resources WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM chapter_structure WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM prompt_templates WHERE version_id = {sql_literal(VERSION_ID)};",
        f"DELETE FROM quality_checklist WHERE version_id = {sql_literal(VERSION_ID)};",
        "",
    ]

    _append_chapter_structure(lines, package.data.get("Chapter_Structure", []))
    _append_answer_cards(lines, package.answer_cards)
    _append_knowledge_points(lines, package.knowledge_points)
    _append_source_chunks(lines, package.source_chunks)
    _append_simple_rows(lines, "concept_comparisons", "comparison_id", package.data.get("Concept_Comparison", []), _comparison_values)
    _append_simple_rows(lines, "synonym_questions", "synonym_id", package.synonyms, _synonym_values)
    _append_simple_rows(lines, "knowledge_relations", "relation_id", package.data.get("Knowledge_Relations", []), _relation_values)
    _append_simple_rows(lines, "resources", "resource_id", package.resources, _resource_values)
    _append_simple_rows(lines, "interactive_scripts", "script_id", package.interactive_scripts, _interactive_script_values)
    _append_simple_rows(lines, "exercises", "exercise_id", package.data.get("Exercises", []), _exercise_values)
    _append_simple_rows(lines, "qa_evaluation_testset", "test_id", package.qa_cases, _qa_values)
    _append_simple_rows(lines, "resource_evaluation_testset", "test_id", package.resource_eval_cases, _resource_qa_values)
    _append_simple_rows(lines, "rag_config", "object_id, version_id, object_type", package.rag_config, _rag_values)
    _append_simple_rows(lines, "embedding_corpus", "embedding_id", package.data.get("Embedding_Corpus", []), _embedding_values)
    _append_simple_rows(lines, "prompt_templates", "template_id", package.data.get("Prompt_Templates", []), _prompt_values)
    _append_simple_rows(lines, "quality_checklist", "check_id", package.data.get("Quality_Checklist", []), _quality_values)

    lines.extend(["", "COMMIT;", ""])
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _infer_chapter_id(package: KnowledgePackage) -> str:
    for table in ("Chapter_Structure", "Answer_Cards", "Knowledge_Points", "Resources"):
        rows = package.data.get(table, [])
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("chapter_id"):
                    return str(row["chapter_id"])
    return CHAPTER_ID


def _infer_chapter_title(package: KnowledgePackage) -> str:
    rows = package.data.get("Chapter_Structure", [])
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and str(row.get("level") or "").lower() in {"chapter", "章"} and row.get("title"):
                return str(row["title"])
        for row in rows:
            if isinstance(row, dict) and row.get("title"):
                return str(row["title"])
    metadata = package.data.get("metadata") or package.data.get("README")
    if isinstance(metadata, dict):
        return str(metadata.get("title") or metadata.get("chapter_title") or _infer_chapter_id(package))
    return _infer_chapter_id(package)


def _infer_version(package: KnowledgePackage) -> str:
    metadata = package.data.get("metadata") or package.data.get("README")
    if isinstance(metadata, dict) and metadata.get("version"):
        return str(metadata["version"])
    if isinstance(metadata, list):
        for row in metadata:
            if isinstance(row, dict) and row.get("field") == "version" and row.get("value"):
                return str(row["value"])
    return VERSION


def _append_chapter_structure(lines: list[str], rows: list[dict[str, Any]]) -> None:
    lines.append("-- Chapter_Structure")
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "INSERT INTO chapter_structure (node_id, version_id, parent_id, level, title, learning_role, summary, raw) VALUES "
            f"({sql_literal(row.get('node_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('parent_id'))}, "
            f"{sql_literal(row.get('level'))}, {sql_literal(row.get('title'))}, {sql_literal(row.get('learning_role'))}, "
            f"{sql_literal(row.get('summary'))}, {jsonb_literal(row)}) "
            "ON CONFLICT (node_id) DO UPDATE SET raw = EXCLUDED.raw;"
        )
    lines.append("")


def _append_answer_cards(lines: list[str], rows: list[dict[str, Any]]) -> None:
    lines.append("-- Answer_Cards")
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "INSERT INTO answer_cards (answer_id, version_id, chapter_id, section_id, canonical_question, question_type, "
            "student_question_patterns, related_kps, answer_mode, answer_points, concise_answer, expanded_answer, "
            "must_include, avoid_content, evidence_chunks, source_excerpt, answer_boundary, recommended_resources, "
            "confidence_rule, status, raw) VALUES "
            f"({sql_literal(row.get('answer_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('chapter_id'))}, "
            f"{sql_literal(row.get('section_id'))}, {sql_literal(row.get('canonical_question'))}, {sql_literal(row.get('question_type'))}, "
            f"{jsonb_literal(row.get('student_question_patterns', []))}, {jsonb_literal(row.get('related_kps', []))}, "
            f"{sql_literal(row.get('answer_mode'))}, {jsonb_literal(row.get('answer_points', []))}, "
            f"{sql_literal(row.get('concise_answer'))}, {sql_literal(row.get('expanded_answer'))}, "
            f"{jsonb_literal(row.get('must_include', []))}, {jsonb_literal(row.get('avoid_content', []))}, "
            f"{jsonb_literal(row.get('evidence_chunks'))}, {sql_literal(row.get('source_excerpt'))}, "
            f"{sql_literal(row.get('answer_boundary'))}, {jsonb_literal(row.get('recommended_resources', []))}, "
            f"{sql_literal(row.get('confidence_rule'))}, {sql_literal(row.get('status'))}, {jsonb_literal(row)}) "
            "ON CONFLICT (answer_id) DO UPDATE SET "
            "version_id = EXCLUDED.version_id, chapter_id = EXCLUDED.chapter_id, section_id = EXCLUDED.section_id, "
            "canonical_question = EXCLUDED.canonical_question, question_type = EXCLUDED.question_type, "
            "student_question_patterns = EXCLUDED.student_question_patterns, related_kps = EXCLUDED.related_kps, "
            "answer_mode = EXCLUDED.answer_mode, answer_points = EXCLUDED.answer_points, "
            "concise_answer = EXCLUDED.concise_answer, expanded_answer = EXCLUDED.expanded_answer, "
            "must_include = EXCLUDED.must_include, avoid_content = EXCLUDED.avoid_content, "
            "evidence_chunks = EXCLUDED.evidence_chunks, source_excerpt = EXCLUDED.source_excerpt, "
            "answer_boundary = EXCLUDED.answer_boundary, recommended_resources = EXCLUDED.recommended_resources, "
            "confidence_rule = EXCLUDED.confidence_rule, status = EXCLUDED.status, raw = EXCLUDED.raw;"
        )
    lines.append("")


def _append_knowledge_points(lines: list[str], rows: list[dict[str, Any]]) -> None:
    lines.append("-- Knowledge_Points")
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "INSERT INTO knowledge_points (kp_id, version_id, chapter_id, section_id, title, knowledge_type, importance, difficulty, "
            "definition, core_explanation, plain_explanation, engineering_meaning, application_scenario, key_points, keywords, aliases, "
            "related_kps, common_mistakes, correction_explanation, answer_strategy, answer_boundary, source_hint, status, raw) VALUES "
            f"({sql_literal(row.get('kp_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('chapter_id'))}, {sql_literal(row.get('section_id'))}, "
            f"{sql_literal(row.get('title'))}, {sql_literal(row.get('knowledge_type'))}, {sql_literal(row.get('importance'))}, {sql_literal(row.get('difficulty'))}, "
            f"{sql_literal(row.get('definition'))}, {sql_literal(row.get('core_explanation'))}, {sql_literal(row.get('plain_explanation'))}, "
            f"{sql_literal(row.get('engineering_meaning'))}, {sql_literal(row.get('application_scenario'))}, {jsonb_literal(row.get('key_points', []))}, "
            f"{jsonb_literal(row.get('keywords', []))}, {jsonb_literal(row.get('aliases', []))}, {jsonb_literal(row.get('related_kps', []))}, "
            f"{jsonb_literal(row.get('common_mistakes', []))}, {sql_literal(row.get('correction_explanation'))}, {sql_literal(row.get('answer_strategy'))}, "
            f"{sql_literal(row.get('answer_boundary'))}, {sql_literal(row.get('source_hint'))}, {sql_literal(row.get('status'))}, {jsonb_literal(row)}) "
            "ON CONFLICT (kp_id) DO UPDATE SET raw = EXCLUDED.raw;"
        )
    lines.append("")


def _append_source_chunks(lines: list[str], rows: list[dict[str, Any]]) -> None:
    lines.append("-- Source_Chunks")
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "INSERT INTO source_chunks (chunk_id, version_id, chapter_id, section_id, heading_path, content_type, evidence_role, "
            "source_excerpt, keywords, usable_for_answer, review_status, raw) VALUES "
            f"({sql_literal(row.get('chunk_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('chapter_id'))}, {sql_literal(row.get('section_id'))}, "
            f"{sql_literal(row.get('heading_path'))}, {sql_literal(row.get('content_type'))}, {sql_literal(row.get('evidence_role'))}, "
            f"{sql_literal(row.get('source_excerpt'))}, {jsonb_literal(row.get('keywords', []))}, {sql_literal(row.get('usable_for_answer'))}, "
            f"{sql_literal(row.get('review_status'))}, {jsonb_literal(row)}) "
            "ON CONFLICT (chunk_id) DO UPDATE SET "
            "version_id = EXCLUDED.version_id, chapter_id = EXCLUDED.chapter_id, section_id = EXCLUDED.section_id, "
            "heading_path = EXCLUDED.heading_path, content_type = EXCLUDED.content_type, "
            "evidence_role = EXCLUDED.evidence_role, source_excerpt = EXCLUDED.source_excerpt, "
            "keywords = EXCLUDED.keywords, usable_for_answer = EXCLUDED.usable_for_answer, "
            "review_status = EXCLUDED.review_status, raw = EXCLUDED.raw;"
        )
    lines.append("")


def _append_simple_rows(lines: list[str], table: str, conflict: str, rows: list[dict[str, Any]], value_fn) -> None:
    lines.append(f"-- {table}")
    for row in rows:
        if not isinstance(row, dict):
            continue
        columns, values = value_fn(row)
        update_clause = _upsert_update_clause(columns, conflict)
        lines.append(
            f"INSERT INTO {table} ({columns}) VALUES ({values}) "
            f"ON CONFLICT ({conflict}) DO UPDATE SET {update_clause};"
        )
    lines.append("")


def _upsert_update_clause(columns: str, conflict: str) -> str:
    cols = [col.strip() for col in columns.split(",")]
    conflict_cols = {col.strip() for col in conflict.split(",")}
    update_cols = [col for col in cols if col not in conflict_cols]
    if not update_cols:
        return ", ".join(f"{col} = EXCLUDED.{col}" for col in cols)
    return ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)


def _comparison_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "comparison_id, version_id, title, chapter_id, dimensions, answer_use, related_answer_cards, status, raw"
    vals = [
        row.get("comparison_id"), VERSION_ID, row.get("title"), row.get("chapter_id"), row.get("dimensions"),
        row.get("answer_use"), row.get("related_answer_cards"), row.get("status"),
    ]
    return cols, ", ".join(sql_literal(v) for v in vals) + ", " + jsonb_literal(row)


def _synonym_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "synonym_id, version_id, standard_term, alias_or_question, type, target_id, priority, raw"
    vals = [row.get("synonym_id"), VERSION_ID, row.get("standard_term"), row.get("alias_or_question"), row.get("type"), row.get("target_id"), row.get("priority")]
    return cols, ", ".join(sql_literal(v) for v in vals[:-1]) + f", {_int_value(vals[-1])}, " + jsonb_literal(row)


def _relation_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "relation_id, version_id, source_id, relation_type, target_id, weight, description, use_in_recommendation, use_in_rag, raw"
    return cols, (
        f"{sql_literal(row.get('relation_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('source_id'))}, "
        f"{sql_literal(row.get('relation_type'))}, {sql_literal(row.get('target_id'))}, {float(row.get('weight') or 1)}, "
        f"{sql_literal(row.get('description'))}, {bool_literal(row.get('use_in_recommendation'))}, "
        f"{bool_literal(row.get('use_in_rag'))}, {jsonb_literal(row)}"
    )


def _resource_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "resource_id, version_id, chapter_id, resource_type, title, file_path, description, related_kps, teaching_use, qa_use, status, raw"
    vals = [
        row.get("resource_id"), VERSION_ID, row.get("chapter_id"), row.get("resource_type"),
        row.get("title"), row.get("file_path"), row.get("description"),
    ]
    tail = [row.get("teaching_use"), row.get("qa_use"), row.get("status")]
    return (
        cols,
        ", ".join(sql_literal(v) for v in vals)
        + ", "
        + jsonb_literal(row.get("related_kps", []))
        + ", "
        + ", ".join(sql_literal(v) for v in tail)
        + ", "
        + jsonb_literal(row),
    )


def _interactive_script_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = (
        "script_id, version_id, resource_id, chapter_id, title, file_path, interaction_theme, "
        "display_objects, operation_steps, trigger_questions, related_kps, extracted_labels, status, raw"
    )
    vals = [
        row.get("script_id"),
        VERSION_ID,
        row.get("resource_id"),
        row.get("chapter_id"),
        row.get("title"),
        row.get("file_path"),
        row.get("interaction_theme"),
    ]
    return (
        cols,
        ", ".join(sql_literal(v) for v in vals)
        + ", "
        + jsonb_literal(row.get("display_objects", []))
        + ", "
        + jsonb_literal(row.get("operation_steps", []))
        + ", "
        + jsonb_literal(row.get("trigger_questions", []))
        + ", "
        + jsonb_literal(row.get("related_kps", []))
        + ", "
        + jsonb_literal(row.get("extracted_labels", []))
        + ", "
        + sql_literal(row.get("status"))
        + ", "
        + jsonb_literal(row),
    )


def _exercise_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "exercise_id, version_id, chapter_id, question, question_type, related_kps, standard_answer_points, grading_rubric, common_mistakes, feedback_template, expected_answer_card, raw"
    return cols, (
        f"{sql_literal(row.get('exercise_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('chapter_id'))}, {sql_literal(row.get('question'))}, "
        f"{sql_literal(row.get('question_type'))}, {jsonb_literal(row.get('related_kps', []))}, {jsonb_literal(row.get('standard_answer_points', []))}, "
        f"{sql_literal(row.get('grading_rubric'))}, {sql_literal(row.get('common_mistakes'))}, {sql_literal(row.get('feedback_template'))}, "
        f"{sql_literal(row.get('expected_answer_card'))}, {jsonb_literal(row)}"
    )


def _qa_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "test_id, version_id, question, expected_answer_card, expected_kps, expected_answer_points, should_not_include, required_response_mode, pass_rule, error_reason, raw"
    return cols, (
        f"{sql_literal(row.get('test_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('question'))}, {sql_literal(row.get('expected_answer_card'))}, "
        f"{jsonb_literal(row.get('expected_kps', []))}, {jsonb_literal(row.get('expected_answer_points', []))}, {jsonb_literal(row.get('should_not_include', []))}, "
        f"{sql_literal(row.get('required_response_mode'))}, {sql_literal(row.get('pass_rule'))}, {sql_literal(row.get('error_reason'))}, {jsonb_literal(row)}"
    )


def _resource_qa_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = (
        "test_id, version_id, chapter_id, question, expected_resource_id, expected_resource_type, "
        "expected_answer_mode, related_kps, resource_intent, pass_rule, raw"
    )
    return cols, (
        f"{sql_literal(row.get('test_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('chapter_id'))}, "
        f"{sql_literal(row.get('question'))}, {sql_literal(row.get('expected_resource_id'))}, "
        f"{sql_literal(row.get('expected_resource_type'))}, {sql_literal(row.get('expected_answer_mode'))}, "
        f"{jsonb_literal(row.get('related_kps', []))}, {sql_literal(row.get('resource_intent'))}, "
        f"{sql_literal(row.get('pass_rule'))}, {jsonb_literal(row)}"
    )


def _rag_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "object_id, version_id, object_type, retrieval_priority, index_text, answer_mode, allow_ai_extension, need_citation, primary_output, fallback_only, notes, raw"
    return cols, (
        f"{sql_literal(row.get('object_id'))}, {sql_literal(VERSION_ID)}, {sql_literal(row.get('object_type'))}, {_int_value(row.get('retrieval_priority'))}, "
        f"{sql_literal(row.get('index_text'))}, {sql_literal(row.get('answer_mode'))}, {sql_literal(row.get('allow_ai_extension'))}, "
        f"{bool_literal(row.get('need_citation'))}, {bool_literal(row.get('primary_output'))}, {bool_literal(row.get('fallback_only'))}, "
        f"{sql_literal(row.get('notes'))}, {jsonb_literal(row)}"
    )


def _int_value(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, int):
        return value
    text = str(value)
    match = re.search(r"-?\d+", text)
    return int(match.group(0)) if match else 0


def _embedding_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "embedding_id, version_id, source_type, source_id, embedding_text, metadata, raw"
    vals = [row.get("embedding_id"), VERSION_ID, row.get("source_type"), row.get("source_id"), row.get("embedding_text"), row.get("metadata")]
    return cols, ", ".join(sql_literal(v) for v in vals) + ", " + jsonb_literal(row)


def _prompt_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "template_id, version_id, name, trigger, template, raw"
    vals = [row.get("template_id"), VERSION_ID, row.get("name"), row.get("trigger"), row.get("template")]
    return cols, ", ".join(sql_literal(v) for v in vals) + ", " + jsonb_literal(row)


def _quality_values(row: dict[str, Any]) -> tuple[str, str]:
    cols = "check_id, version_id, item, criterion, status, raw"
    vals = [row.get("check_id"), VERSION_ID, row.get("item"), row.get("criterion"), row.get("status")]
    return cols, ", ".join(sql_literal(v) for v in vals) + ", " + jsonb_literal(row)
