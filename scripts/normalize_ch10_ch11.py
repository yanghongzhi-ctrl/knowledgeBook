from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path("C:/Users/Michael/Desktop/knowledge")
ENRICHMENT_PATH = ROOT / "output" / "ch10_ch11_word_enrichment_2026-06-05.json"
BOUNDARY_REVIEW_PATH = ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.json"
EVIDENCE_GRADING_PATH = ROOT / "data" / "review" / "ch10_ch11_full_source_boundary_manual_approvals.proposed.json"
MANUAL_APPROVALS_PATH = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.json"
ASSET_ROOT = Path("F:/编书/道路工程数字设计方法/05脚本及图片素材")

CHAPTERS = {
    "ch10": {
        "json_pattern": "第10章*知识库*.json",
        "jsonl_pattern": "第10章*.jsonl",
        "title": "AI驱动的道路设计方法",
        "script_pattern": "10.*.html",
        "special_tables": ["Method_Cards", "Application_Scenarios", "Case_Cards", "Risk_and_Limitations"],
    },
    "ch11": {
        "json_pattern": "第11章*知识库*.json",
        "jsonl_pattern": "第11章*.jsonl",
        "title": "道路数字孪生的概念与方法体系",
        "script_pattern": "11.*.html",
        "special_tables": ["Technology_Frameworks", "Process_Cards", "Application_Scenarios", "Case_Cards", "Risk_and_Limitations"],
    },
}

REQUIRED_LIST_TABLES = [
    "Chapter_Structure",
    "Source_Chunks",
    "Knowledge_Points",
    "Answer_Cards",
    "Concept_Comparison",
    "Synonyms_Questions",
    "Knowledge_Relations",
    "Resources",
    "Interactive_Scripts",
    "Exercises",
    "QA_Evaluation_Testset",
    "RAG_Config",
    "Embedding_Corpus",
    "Prompt_Templates",
    "Quality_Checklist",
    "Resource_Evaluation_Testset",
    "Answer_Guardrails",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize chapter 10-11 method/framework knowledge packages.")
    parser.add_argument("--chapters", nargs="+", default=list(CHAPTERS), choices=sorted(CHAPTERS))
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--asset-root", type=Path, default=ASSET_ROOT)
    parser.add_argument("--enrichment", type=Path, default=ENRICHMENT_PATH)
    parser.add_argument("--boundary-review", type=Path, default=BOUNDARY_REVIEW_PATH)
    parser.add_argument("--evidence-grading", type=Path, default=EVIDENCE_GRADING_PATH)
    parser.add_argument("--manual-approvals", type=Path, default=MANUAL_APPROVALS_PATH)
    args = parser.parse_args()

    summaries = []
    for chapter_id in args.chapters:
        summaries.append(
            normalize_chapter(
                chapter_id,
                args.source_dir,
                args.asset_root,
                args.enrichment,
                args.boundary_review,
                args.evidence_grading,
                args.manual_approvals,
            )
        )
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


def normalize_chapter(
    chapter_id: str,
    source_dir: Path,
    asset_root: Path,
    enrichment_path: Path,
    boundary_review_path: Path,
    evidence_grading_path: Path,
    manual_approvals_path: Path,
) -> dict[str, Any]:
    config = CHAPTERS[chapter_id]
    source_json = first_match(source_dir, config["json_pattern"])
    source_jsonl = first_match(source_dir, config["jsonl_pattern"], required=False)
    raw = json.loads(source_json.read_text(encoding="utf-8-sig"))
    data = raw.get("sheets") if isinstance(raw.get("sheets"), dict) else raw
    data = {key: value for key, value in data.items()}
    if isinstance(raw.get("metadata"), dict):
        data["metadata"] = raw["metadata"]

    normalize_package(
        chapter_id,
        data,
        config,
        asset_root,
        enrichment_path,
        boundary_review_path,
        evidence_grading_path,
        manual_approvals_path,
    )

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


def first_match(root: Path, pattern: str, required: bool = True) -> Path | None:
    matches = sorted(root.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if matches:
        return matches[0]
    if required:
        raise SystemExit(f"Cannot find {pattern} under {root}")
    return None


def normalize_package(
    chapter_id: str,
    data: dict[str, Any],
    config: dict[str, Any],
    asset_root: Path,
    enrichment_path: Path,
    boundary_review_path: Path,
    evidence_grading_path: Path,
    manual_approvals_path: Path,
) -> None:
    ensure_list_tables(data, config)
    normalize_chapter_structure(data.get("Chapter_Structure", []))
    normalize_source_chunks(data.get("Source_Chunks", []))
    normalize_knowledge_points(data.get("Knowledge_Points", []))
    normalize_answer_cards(data.get("Answer_Cards", []))
    normalize_concept_comparisons(data.get("Concept_Comparison", []), chapter_id)
    normalize_special_tables(data, config)
    normalize_synonyms_table(data, chapter_id)
    normalize_qa_cases(data, chapter_id)
    normalize_embedding_corpus(data.get("Embedding_Corpus", []), chapter_id)
    normalize_rag_config(data.get("RAG_Config", []), chapter_id)
    normalize_resources(data.get("Resources", []), chapter_id)
    bind_interactive_scripts(data, chapter_id, config, asset_root)
    normalize_resource_eval(data, chapter_id)
    normalize_guardrails(data, chapter_id)
    normalize_quality_checklist(data.get("Quality_Checklist", []), chapter_id)
    data["Prompt_Templates"] = prompt_templates(chapter_id)
    repair_known_text_artifacts(data)
    apply_word_enrichment(data, chapter_id, enrichment_path)
    apply_curated_question_aliases(data, chapter_id)
    apply_source_boundary_review(data, chapter_id, boundary_review_path, evidence_grading_path, manual_approvals_path)
    data.setdefault("metadata", {})
    if isinstance(data["metadata"], dict):
        data["metadata"].update(
            {
                "chapter_id": chapter_id,
                "chapter_title": config["title"],
                "normalized_by": "scripts/normalize_ch10_ch11.py",
                "normalization_profile": "method_framework",
            }
        )


def ensure_list_tables(data: dict[str, Any], config: dict[str, Any]) -> None:
    for table in [*REQUIRED_LIST_TABLES, *config["special_tables"], "Synonyms"]:
        if not isinstance(data.get(table), list):
            data[table] = []


def normalize_chapter_structure(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row.setdefault("order", index)
        row["level"] = normalize_level(row.get("level"), row.get("node_type"))
        row["title"] = row.get("title") or row.get("node_title") or row.get("name") or ""
        row.setdefault("knowledge_focus", row.get("summary") or row.get("description") or "")


def normalize_level(level: Any, node_type: Any) -> str:
    text = str(level or node_type or "").lower()
    if text in {"chapter", "1"}:
        return "chapter"
    if text in {"section", "2"}:
        return "section"
    if text in {"subsection", "3"}:
        return "subsection"
    if text in {"learning_goal"}:
        return "learning_goal"
    return str(level or node_type or "")


def normalize_source_chunks(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        row["chunk_summary"] = row.get("chunk_summary") or row.get("semantic_summary") or row.get("summary") or row.get("source_excerpt") or ""
        row.setdefault("evidence_role", row.get("evidence_role") or "教材证据层，不作为RAG第一主检索对象")
        row.setdefault("answer_use", row.get("use_in_rag") or row.get("use_policy") or "用于核验答案卡与方法/框架卡，不建议整段输出给学生")
        row["usable_for_answer"] = "no_direct_output"
        row.setdefault("review_status", row.get("status") or "checked")
        row["keywords"] = split_values(row.get("keywords"))


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
        row["aliases"] = split_values(row.get("aliases")) or split_values(row.get("student_question_patterns"))[:4]
        row["related_kps"] = split_values(row.get("related_kps"))
        row["common_mistakes"] = split_values(row.get("common_mistakes"))
        row.setdefault("source_hint", ";".join(split_values(row.get("source_chunks") or row.get("evidence_chunks"))))
        row.setdefault("status", "checked")


def normalize_answer_cards(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        row["student_question_patterns"] = split_values(row.get("student_question_patterns"))
        row["related_kps"] = split_values(row.get("related_kps"))
        row["answer_points"] = split_values(row.get("answer_points")) or split_values(row.get("must_include"))
        row["must_include"] = split_values(row.get("must_include")) or row["answer_points"][:4]
        row["avoid_content"] = split_values(row.get("avoid_content"))
        row["evidence_chunks"] = split_values(row.get("evidence_chunks") or row.get("source_chunks"))
        row["recommended_resources"] = split_values(row.get("recommended_resources"))
        row.setdefault("concise_answer", "；".join(row["answer_points"][:2]))
        row.setdefault("expanded_answer", "；".join(row["answer_points"]))
        row.setdefault("status", "checked")


def normalize_concept_comparisons(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        row.setdefault("chapter_id", chapter_id)
        object_a = str(row.get("object_a") or row.get("concept_a") or "").strip()
        object_b = str(row.get("object_b") or row.get("concept_b") or "").strip()
        dimension = str(row.get("comparison_dimension") or row.get("dimension") or "").strip()
        if not row.get("title"):
            if object_a and object_b and dimension:
                row["title"] = f"{object_a}与{object_b}对比：{dimension}"
            elif object_a and object_b:
                row["title"] = f"{object_a}与{object_b}对比"
            else:
                row["title"] = row.get("comparison_id") or "概念对比"
        row.setdefault("dimensions", dimension)
        row.setdefault("answer_use", row.get("teaching_conclusion") or row.get("qa_trigger") or "")
        row["related_answer_cards"] = split_values(row.get("related_answer_cards"))
        row["related_kps"] = split_values(row.get("related_kps"))
        row.setdefault("status", "checked")


def normalize_special_tables(data: dict[str, Any], config: dict[str, Any]) -> None:
    for table in config["special_tables"]:
        for index, row in enumerate(data.get(table, []), 1):
            if not isinstance(row, dict):
                continue
            row.setdefault("chapter_id", data.get("metadata", {}).get("chapter_id", ""))
            row.setdefault("status", "checked")
            row.setdefault("order", index)


def normalize_synonyms_table(data: dict[str, Any], chapter_id: str) -> None:
    rows = []
    for index, row in enumerate(data.get("Synonyms", []), 1):
        if not isinstance(row, dict):
            continue
        target_id = row.get("kp_id") or row.get("target_id") or row.get("object_id") or ""
        question = row.get("student_expression") or row.get("alias_or_question") or row.get("standard_term") or ""
        if not question:
            continue
        synonym_id = row.get("synonym_id") or row.get("syn_id") or f"{chapter_id}_synq_{index:04d}"
        match_type = row.get("expression_type") or row.get("match_type") or "alias"
        rows.append(
            {
                "synonym_id": synonym_id,
                "question_id": synonym_id,
                "chapter_id": chapter_id,
                "target_id": target_id,
                "question": question,
                "alias_or_question": question,
                "standard_term": row.get("standard_term") or "",
                "match_type": match_type,
                "type": match_type,
                "priority": row.get("priority") or 1,
            }
        )
    data["Synonyms_Questions"] = rows


def normalize_qa_cases(data: dict[str, Any], chapter_id: str) -> None:
    cards = {str(row.get("answer_id")): row for row in data.get("Answer_Cards", []) if isinstance(row, dict)}
    normalized = []
    source_rows = data.get("QA_Evaluation_Testset") or data.get("QA_Testset") or []
    for index, row in enumerate(source_rows, 1):
        if not isinstance(row, dict):
            continue
        expected = str(row.get("expected_answer_card") or row.get("expected_route") or "")
        card = cards.get(expected, {})
        answer_points = split_values(row.get("expected_answer_points") or row.get("must_include"))
        if not answer_points and card:
            answer_points = split_values(card.get("answer_points"))
        normalized.append(
            {
                "test_id": row.get("test_id") or row.get("eval_id") or f"{chapter_id}_qa_{index:04d}",
                "chapter_id": chapter_id,
                "question": row.get("question") or "",
                "expected_answer_card": expected,
                "expected_answer_points": answer_points,
                "expected_kps": split_values(row.get("expected_kps")),
                "should_not_include": split_values(row.get("should_not_include")),
                "status": row.get("status") or "checked",
                "required_response_mode": row.get("required_response_mode") or card.get("answer_mode") or "bullet",
                "pass_criteria": row.get("pass_criteria") or row.get("pass_rule") or "",
            }
        )
    data["QA_Evaluation_Testset"] = normalized


def normalize_embedding_corpus(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        object_type = str(row.get("object_type") or row.get("source_type") or "")
        object_id = str(row.get("object_id") or row.get("source_id") or "")
        row["embedding_id"] = row.get("embedding_id") or f"{chapter_id}_emb_{index:04d}"
        row["source_type"] = normalize_source_type(object_type)
        row["source_id"] = object_id
        row["embedding_text"] = row.get("embedding_text") or row.get("text_for_embedding") or row.get("index_text") or object_id


def normalize_source_type(value: str) -> str:
    value = value.strip().lower()
    mapping = {
        "answer_card": "answer_card",
        "answer_cards": "answer_card",
        "knowledge_point": "knowledge_point",
        "knowledge_points": "knowledge_point",
        "resource": "resource",
        "resources": "resource",
        "source_chunk": "source_chunk",
        "source_chunks": "source_chunk",
    }
    return mapping.get(value, value or "knowledge_object")


def normalize_rag_config(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row["config_id"] = row.get("config_id") or f"{chapter_id}_rag_{index:04d}"
        row["chapter_id"] = row.get("chapter_id") or chapter_id
        row["object_type"] = row.get("object_type") or row.get("target_type") or ""
        row["object_id"] = row.get("object_id") or row.get("target_id") or ""
        row["retrieval_keywords"] = split_values(row.get("retrieval_keywords") or row.get("query_intents"))
        row["index_text"] = row.get("index_text") or row.get("embedding_text") or row.get("text_for_embedding") or "；".join(row["retrieval_keywords"]) or row["object_id"]
        row.setdefault("answer_mode", row.get("answer_mode") or "bullet")
        row.setdefault("use_in_rag", True)


def normalize_resources(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        row.setdefault("chapter_id", chapter_id)
        row["related_kps"] = split_values(row.get("related_kps"))
        row.setdefault("priority", row.get("priority") or 1)
        row.setdefault("status", row.get("status") or "placeholder")
        row.setdefault("reference_aliases", [row.get("title"), row.get("resource_id")])


def bind_interactive_scripts(data: dict[str, Any], chapter_id: str, config: dict[str, Any], asset_root: Path) -> None:
    target_dir = ROOT / "assets" / chapter_id / "interactive_html"
    target_dir.mkdir(parents=True, exist_ok=True)
    resources = data.get("Resources", [])
    scripts = []
    existing_resource_ids = {str(row.get("resource_id")) for row in resources if isinstance(row, dict)}

    for index, source_path in enumerate(sorted(asset_root.glob(config["script_pattern"])), 1):
        target_path = target_dir / source_path.name
        shutil.copy2(source_path, target_path)
        resource_id = f"{chapter_id}_script_{index:02d}"
        relative_path = target_path.relative_to(ROOT).as_posix()
        if resource_id not in existing_resource_ids:
            resources.append(
                {
                    "resource_id": resource_id,
                    "chapter_id": chapter_id,
                    "section_id": "",
                    "resource_type": "interactive_html",
                    "title": source_path.stem,
                    "description": f"{config['title']}互动脚本：{source_path.stem}",
                    "file_path": relative_path,
                    "related_kps": [],
                    "teaching_use": "用于按主题浏览本章方法、框架或案例逻辑。",
                    "qa_use": "学生明确要求查看互动脚本或学习流程时推荐。",
                    "priority": 1,
                    "status": "bound",
                    "reference_aliases": [source_path.stem, resource_id],
                }
            )
        else:
            for row in resources:
                if isinstance(row, dict) and row.get("resource_id") == resource_id:
                    row["file_path"] = relative_path
                    row["status"] = "bound"
                    row["resource_type"] = "interactive_html"
                    break
        scripts.append(
            {
                "script_id": f"{chapter_id}_interactive_{index:02d}",
                "chapter_id": chapter_id,
                "resource_id": resource_id,
                "title": source_path.stem,
                "file_path": relative_path,
                "status": "bound",
                "teaching_use": "互动浏览本章知识结构、方法流程和典型应用。",
            }
        )
    data["Interactive_Scripts"] = scripts


def normalize_resource_eval(data: dict[str, Any], chapter_id: str) -> None:
    cases = []
    for index, resource in enumerate(data.get("Resources", []), 1):
        if not isinstance(resource, dict):
            continue
        if resource.get("status") != "bound":
            continue
        cases.append(
            {
                "test_id": f"{chapter_id}_res_eval_{index:03d}",
                "chapter_id": chapter_id,
                "question": f"我想看{resource.get('title')}。",
                "expected_resource_id": resource.get("resource_id"),
                "expected_resource_type": resource.get("resource_type"),
                "pass_criteria": "能够返回并打开已绑定资源。",
                "status": "checked",
            }
        )
    data["Resource_Evaluation_Testset"] = cases


def normalize_guardrails(data: dict[str, Any], chapter_id: str) -> None:
    source = data.get("Answer_Guardrails") or data.get("Answer_Constraints") or []
    rows = []
    for index, row in enumerate(source, 1):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "guardrail_id": row.get("guardrail_id") or row.get("constraint_id") or f"{chapter_id}_guard_{index:03d}",
                "chapter_id": chapter_id,
                "title": row.get("constraint_name") or row.get("title") or row.get("risk_title") or f"回答约束{index}",
                "rule": row.get("description") or row.get("rule") or row.get("mitigation") or "",
                "severity": row.get("severity") or "medium",
                "status": "checked",
            }
        )
    data["Answer_Guardrails"] = rows


def normalize_quality_checklist(rows: list[dict[str, Any]], chapter_id: str) -> None:
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row["check_id"] = row.get("check_id") or f"{chapter_id}_quality_{index:03d}"
        row["item"] = row.get("item") or row.get("check_item") or row.get("title") or ""
        row["criterion"] = row.get("criterion") or row.get("notes") or row.get("level") or ""
        row.setdefault("status", "checked")


def prompt_templates(chapter_id: str) -> list[dict[str, str]]:
    return [
        {
            "template_id": f"{chapter_id}_concept_answer",
            "chapter_id": chapter_id,
            "name": "Concept or method answer",
            "trigger": "concept_or_method",
            "intent": "concept_or_method",
            "template": "先给出概念或方法定位，再说明工程意义、适用场景和边界条件。",
        },
        {
            "template_id": f"{chapter_id}_comparison_answer",
            "chapter_id": chapter_id,
            "name": "Comparison answer",
            "trigger": "comparison",
            "intent": "comparison",
            "template": "用对比维度组织回答，突出差异、适用对象和教学结论。",
        },
    ]


def repair_known_text_artifacts(value: Any) -> Any:
    replacements = {
        "实现动。": "实现动态同步、状态预测与闭环优化。",
        "转型。。": "转型。",
    }
    if isinstance(value, dict):
        for key, item in list(value.items()):
            value[key] = repair_known_text_artifacts(item)
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = repair_known_text_artifacts(item)
        return value
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value
    return value


def apply_word_enrichment(data: dict[str, Any], chapter_id: str, enrichment_path: Path) -> None:
    if not enrichment_path.exists():
        return
    enrichment = json.loads(enrichment_path.read_text(encoding="utf-8"))
    chapter = (enrichment.get("chapters") or {}).get(chapter_id)
    if not isinstance(chapter, dict):
        return
    apply_data = chapter.get("apply") if isinstance(chapter.get("apply"), dict) else {}
    applied = {
        "heading_aliases": apply_heading_aliases(data, chapter_id, apply_data.get("heading_aliases") or []),
        "answer_cards": apply_answer_card_support(data, apply_data.get("answer_card_support") or []),
        "source_chunks": apply_source_chunk_notes(data, apply_data.get("source_chunk_notes") or []),
    }
    data.setdefault("metadata", {})
    if isinstance(data["metadata"], dict):
        data["metadata"]["word_enrichment"] = {
            "source": str(enrichment_path),
            "applied": applied,
            "summary": chapter.get("summary") or {},
        }


def apply_heading_aliases(data: dict[str, Any], chapter_id: str, aliases: list[dict[str, Any]]) -> int:
    structure_by_id = {
        str(row.get("node_id") or row.get("section_id") or row.get("title") or ""): row
        for row in data.get("Chapter_Structure", [])
        if isinstance(row, dict)
    }
    kp_by_id = {str(row.get("kp_id")): row for row in data.get("Knowledge_Points", []) if isinstance(row, dict)}
    card_by_id = {str(row.get("answer_id")): row for row in data.get("Answer_Cards", []) if isinstance(row, dict)}
    res_by_id = {str(row.get("resource_id")): row for row in data.get("Resources", []) if isinstance(row, dict)}
    rag_by_key = {
        (str(row.get("object_type")), str(row.get("object_id"))): row
        for row in data.get("RAG_Config", [])
        if isinstance(row, dict)
    }
    synonym_rows = data.get("Synonyms_Questions", [])
    existing_synonyms = {
        (str(row.get("target_id")), str(row.get("alias_or_question") or row.get("question")))
        for row in synonym_rows
        if isinstance(row, dict)
    }
    applied = 0
    for index, item in enumerate(aliases, 1):
        if not isinstance(item, dict) or not item.get("auto_apply"):
            continue
        heading = str(item.get("heading") or "").strip()
        target_type = str(item.get("target_type") or "")
        target_id = str(item.get("target_id") or "")
        if not heading or not target_id:
            continue
        target = None
        object_type = target_type
        if target_type == "chapter_structure":
            target = structure_by_id.get(target_id)
            object_type = "chapter_structure"
            if target is not None:
                target["aliases"] = unique_list(split_values(target.get("aliases")) + [heading])
                target["keywords"] = unique_list(split_values(target.get("keywords")) + [heading])
                target["word_heading_aliases"] = unique_list(split_values(target.get("word_heading_aliases")) + [heading])
        elif target_type == "knowledge_point":
            target = kp_by_id.get(target_id)
            if target is not None:
                target["aliases"] = unique_list(split_values(target.get("aliases")) + [heading])
                target["keywords"] = unique_list(split_values(target.get("keywords")) + [heading])
                target["word_heading_aliases"] = unique_list(split_values(target.get("word_heading_aliases")) + [heading])
        elif target_type == "answer_card":
            target = card_by_id.get(target_id)
            if target is not None:
                target["student_question_patterns"] = unique_list(split_values(target.get("student_question_patterns")) + [heading])
                target["word_heading_aliases"] = unique_list(split_values(target.get("word_heading_aliases")) + [heading])
        elif target_type == "resource":
            target = res_by_id.get(target_id)
            object_type = "resource"
            if target is not None:
                target["reference_aliases"] = unique_list(split_values(target.get("reference_aliases")) + [heading])
        if target is None:
            continue
        rag = rag_by_key.get((object_type, target_id))
        if rag is not None:
            rag["retrieval_keywords"] = unique_list(split_values(rag.get("retrieval_keywords")) + [heading])
            rag["index_text"] = "；".join(unique_list([str(rag.get("index_text") or ""), heading]))
        if (target_id, heading) not in existing_synonyms:
            synonym_id = f"{chapter_id}_word_heading_{len(synonym_rows) + index:04d}"
            synonym_rows.append(
                {
                    "synonym_id": synonym_id,
                    "question_id": synonym_id,
                    "chapter_id": chapter_id,
                    "target_id": target_id,
                    "question": heading,
                    "alias_or_question": heading,
                    "standard_term": target.get("title") or target.get("canonical_question") or target.get("resource_id") or target_id,
                    "match_type": "word_heading_alias",
                    "type": "word_heading_alias",
                    "priority": 2,
                }
            )
            existing_synonyms.add((target_id, heading))
        applied += 1
    data["Synonyms_Questions"] = synonym_rows
    return applied


def apply_curated_question_aliases(data: dict[str, Any], chapter_id: str) -> int:
    aliases_by_card = {
        "ch11": {
            "ans_ch11_001": [
                "道路数字孪生是什么？",
                "什么是道路数字孪生？",
                "道路数字孪生的定义是什么？",
            ],
        },
    }
    chapter_aliases = aliases_by_card.get(chapter_id, {})
    if not chapter_aliases:
        return 0

    cards = {str(row.get("answer_id")): row for row in data.get("Answer_Cards", []) if isinstance(row, dict)}
    rag_by_key = {
        (str(row.get("object_type")), str(row.get("object_id"))): row
        for row in data.get("RAG_Config", [])
        if isinstance(row, dict)
    }
    synonym_rows = data.get("Synonyms_Questions", [])
    existing_synonyms = {
        (str(row.get("target_id")), str(row.get("alias_or_question") or row.get("question")))
        for row in synonym_rows
        if isinstance(row, dict)
    }
    applied = 0
    for answer_id, aliases in chapter_aliases.items():
        card = cards.get(answer_id)
        if card is None:
            continue
        existing_patterns = split_values(card.get("student_question_patterns"))
        new_aliases = [alias for alias in aliases if alias not in existing_patterns]
        if not new_aliases:
            continue
        card["student_question_patterns"] = unique_list(existing_patterns + new_aliases)
        card["curated_question_aliases"] = unique_list(split_values(card.get("curated_question_aliases")) + new_aliases)
        rag = rag_by_key.get(("answer_card", answer_id))
        if rag is not None:
            rag["retrieval_keywords"] = unique_list(split_values(rag.get("retrieval_keywords")) + new_aliases)
            rag["index_text"] = "; ".join(unique_list([str(rag.get("index_text") or ""), *new_aliases]))
        for alias in new_aliases:
            if (answer_id, alias) in existing_synonyms:
                continue
            synonym_id = f"{chapter_id}_curated_alias_{len(synonym_rows) + 1:04d}"
            synonym_rows.append(
                {
                    "synonym_id": synonym_id,
                    "question_id": synonym_id,
                    "chapter_id": chapter_id,
                    "target_id": answer_id,
                    "question": alias,
                    "alias_or_question": alias,
                    "standard_term": card.get("canonical_question") or answer_id,
                    "match_type": "curated_question_alias",
                    "type": "curated_question_alias",
                    "priority": 3,
                }
            )
            existing_synonyms.add((answer_id, alias))
        applied += len(new_aliases)
    data["Synonyms_Questions"] = synonym_rows
    return applied


def apply_answer_card_support(data: dict[str, Any], rows: list[dict[str, Any]]) -> int:
    card_by_id = {str(row.get("answer_id")): row for row in data.get("Answer_Cards", []) if isinstance(row, dict)}
    applied = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        card = card_by_id.get(str(item.get("answer_id") or ""))
        if card is None:
            continue
        classification = str(item.get("classification") or "")
        card["word_alignment"] = {
            "word_hit": False,
            "classification": classification,
            "recommended_action": item.get("recommended_action") or "",
            "related_kp_hit": bool(item.get("related_kp_hit")),
            "evidence_statuses": item.get("evidence_statuses") or [],
        }
        if classification == "teaching_rewrite_supported":
            card["support_type"] = "teaching_rewrite_supported"
        applied += 1
    return applied


def apply_source_chunk_notes(data: dict[str, Any], rows: list[dict[str, Any]]) -> int:
    source_by_id = {str(row.get("chunk_id")): row for row in data.get("Source_Chunks", []) if isinstance(row, dict)}
    applied = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        chunk = source_by_id.get(str(item.get("chunk_id") or ""))
        if chunk is None:
            continue
        chunk["word_alignment"] = {
            "status": item.get("word_status") or "",
            "classification": item.get("classification") or "",
            "support_terms": item.get("support_terms") or [],
        }
        chunk["word_correspondence"] = {
            "source": "word_alignment_ch10_ch11_2026-06-04",
            "status": item.get("word_status") or "",
            "classification": item.get("classification") or "",
            "excerpt_preview": item.get("excerpt_preview") or "",
        }
        chunk["evidence_boundary_note"] = item.get("evidence_boundary_note") or ""
        applied += 1
    return applied


def apply_source_boundary_review(
    data: dict[str, Any],
    chapter_id: str,
    boundary_review_path: Path,
    evidence_grading_path: Path,
    manual_approvals_path: Path,
) -> None:
    if not boundary_review_path.exists():
        return
    review = json.loads(boundary_review_path.read_text(encoding="utf-8"))
    chapter = (review.get("chapters") or {}).get(chapter_id)
    if not isinstance(chapter, dict):
        return
    rows = chapter.get("source_boundary_reviews") or []
    source_by_id = {str(row.get("chunk_id")): row for row in data.get("Source_Chunks", []) if isinstance(row, dict)}
    gradings = load_source_boundary_decisions(evidence_grading_path, chapter_id)
    approvals = load_source_boundary_decisions(manual_approvals_path, chapter_id)
    applied = 0
    graded = 0
    approved = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        chunk_id = str(item.get("chunk_id") or "")
        chunk = source_by_id.get(chunk_id)
        if chunk is None:
            continue
        candidates = item.get("top_candidates") or []
        best = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
        grading = gradings.get(chunk_id)
        approval = approvals.get(chunk_id)
        chunk["review_status"] = "needs_evidence_boundary_review"
        chunk["source_excerpt_role"] = item.get("source_excerpt_role") or "needs_evidence_boundary_review"
        chunk["evidence_review"] = {
            "source": str(boundary_review_path),
            "original_classification": item.get("original_classification") or "",
            "review_status": item.get("review_status") or "",
            "recommended_action": item.get("recommended_action") or "",
            "best_score": item.get("best_score") or 0,
            "score_margin": item.get("score_margin") or 0,
            "candidate_paragraph_start": best.get("paragraph_start"),
            "candidate_paragraph_end": best.get("paragraph_end"),
            "candidate_reasons": best.get("reasons") or [],
            "matched_terms": best.get("matched_terms") or [],
            "candidate_text_preview": str(best.get("text") or "")[:240],
            "reviewer_decision": "",
            "reviewer_notes": "",
        }
        if grading:
            apply_automated_source_boundary_grading(chunk, grading, evidence_grading_path)
            graded += 1
        if approval:
            apply_manual_source_boundary_approval(chunk, approval)
            approved += 1
        applied += 1
    data.setdefault("metadata", {})
    if isinstance(data["metadata"], dict):
        data["metadata"]["source_boundary_review"] = {
            "source": str(boundary_review_path),
            "applied": applied,
            "evidence_grading_source": str(evidence_grading_path),
            "evidence_grading_applied": graded,
            "formal_approvals_source": str(manual_approvals_path),
            "formal_approvals_applied": approved,
            "manual_approvals_source": str(manual_approvals_path),
            "manual_approvals_applied": approved,
            "summary": chapter.get("summary") or {},
            "policy": "Automated grading is a publication maintenance signal for this stable textbook knowledge base; Source_Chunks remain evidence-only and are not verbatim textbook quotes. A formal approval file is optional and only overrides automated grading when present.",
        }


def load_source_boundary_decisions(path: Path, chapter_id: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    decisions: dict[str, dict[str, Any]] = {}
    for item in payload.get("decisions", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("chapter_id") or "") != chapter_id:
            continue
        decision = str(item.get("decision") or "").strip()
        chunk_id = str(item.get("chunk_id") or "").strip()
        if not decision or not chunk_id:
            continue
        decisions[chunk_id] = item
    return decisions


def evidence_quality_profile(decision: str) -> dict[str, Any]:
    profiles = {
        "confirm_candidate_anchor": {
            "evidence_confidence": "high",
            "evidence_boundary_type": "concept_anchor",
            "source_excerpt_role": "auto_concept_anchor_not_verbatim",
            "word_verification": "auto_concept_anchor_supported",
            "review_status": "auto_evidence_graded",
            "answer_use": "教材证据层：概念锚点支持，可辅助答案核验；不直接整段输出给学生。",
            "usable_for_answer": "no_direct_output",
            "needs_textbook_anchor_review": False,
        },
        "confirm_teaching_summary": {
            "evidence_confidence": "medium",
            "evidence_boundary_type": "teaching_summary",
            "source_excerpt_role": "auto_teaching_summary_not_verbatim",
            "word_verification": "auto_teaching_summary_supported",
            "review_status": "auto_evidence_graded",
            "answer_use": "教材证据层：支持教学化概括，可辅助答案核验；不作为教材原句引用。",
            "usable_for_answer": "no_direct_output",
            "needs_textbook_anchor_review": False,
        },
        "confirm_boundary_fragment": {
            "evidence_confidence": "medium",
            "evidence_boundary_type": "boundary_fragment",
            "source_excerpt_role": "auto_boundary_fragment_not_verbatim",
            "word_verification": "auto_boundary_fragment_supported",
            "review_status": "auto_evidence_graded",
            "answer_use": "教材证据层：片段边界可支持局部知识点核验；不作为完整答案主证据。",
            "usable_for_answer": "no_direct_output",
            "needs_textbook_anchor_review": False,
        },
        "manual_anchor_pending": {
            "evidence_confidence": "low",
            "evidence_boundary_type": "weak_or_missing_anchor",
            "source_excerpt_role": "auxiliary_evidence_anchor_weak_not_primary",
            "word_verification": "auto_anchor_missing_or_weak",
            "review_status": "auto_evidence_downgraded",
            "answer_use": "辅助证据：教材锚点弱或需更精确，不作为RAG主回答内容。",
            "usable_for_answer": "no_direct_output",
            "needs_textbook_anchor_review": True,
        },
    }
    return profiles.get(
        decision,
        {
            "evidence_confidence": "low",
            "evidence_boundary_type": "unclassified",
            "source_excerpt_role": "auxiliary_evidence_unclassified_not_primary",
            "word_verification": "auto_evidence_unclassified",
            "review_status": "auto_evidence_downgraded",
            "answer_use": "辅助证据：证据边界未分类，不作为RAG主回答内容。",
            "usable_for_answer": "no_direct_output",
            "needs_textbook_anchor_review": True,
        },
    )


def apply_automated_source_boundary_grading(chunk: dict[str, Any], grading: dict[str, Any], grading_path: Path) -> None:
    decision = str(grading.get("decision") or "").strip()
    note = str(grading.get("reviewer_notes") or "").strip()
    profile = evidence_quality_profile(decision)
    review = chunk.setdefault("evidence_review", {})
    if not isinstance(review, dict):
        review = {}
        chunk["evidence_review"] = review

    chunk["review_status"] = profile["review_status"]
    chunk["source_excerpt_role"] = profile["source_excerpt_role"]
    chunk["word_verification"] = profile["word_verification"]
    chunk["usable_for_answer"] = profile["usable_for_answer"]
    chunk["answer_use"] = profile["answer_use"]
    chunk["evidence_quality_profile"] = {
        "source": str(grading_path),
        "mode": "automated_textbook_evidence_grading",
        "decision": decision,
        "priority_group": grading.get("priority_group") or "",
        "evidence_confidence": profile["evidence_confidence"],
        "evidence_boundary_type": profile["evidence_boundary_type"],
        "source_excerpt_role": profile["source_excerpt_role"],
        "word_verification": profile["word_verification"],
        "review_status": profile["review_status"],
        "answer_use": profile["answer_use"],
        "usable_for_answer": profile["usable_for_answer"],
        "needs_textbook_anchor_review": profile["needs_textbook_anchor_review"],
        "not_verbatim_quote": True,
    }

    review["automated_decision"] = decision
    review["automated_notes"] = note
    review["evidence_quality_status"] = profile["evidence_confidence"]
    review["evidence_boundary_type"] = profile["evidence_boundary_type"]
    review["needs_textbook_anchor_review"] = profile["needs_textbook_anchor_review"]
    review["automated_review_status"] = profile["review_status"]
    review["approved_paragraph_start"] = grading.get("approved_paragraph_start")
    review["approved_paragraph_end"] = grading.get("approved_paragraph_end")


def apply_manual_source_boundary_approval(chunk: dict[str, Any], approval: dict[str, Any]) -> None:
    decision = str(approval.get("decision") or "").strip()
    note = str(approval.get("reviewer_notes") or "").strip()
    review = chunk.setdefault("evidence_review", {})
    if not isinstance(review, dict):
        review = {}
        chunk["evidence_review"] = review
    review["reviewer_decision"] = decision
    review["reviewer_notes"] = note
    review["approved_paragraph_start"] = approval.get("approved_paragraph_start")
    review["approved_paragraph_end"] = approval.get("approved_paragraph_end")

    if decision == "confirm_candidate_anchor":
        chunk["review_status"] = "checked"
        chunk["source_excerpt_role"] = "manual_confirmed_concept_anchor_not_verbatim"
        chunk["word_verification"] = "manual_concept_anchor_confirmed"
        review["review_status"] = "manual_confirmed"
    elif decision == "confirm_teaching_summary":
        chunk["review_status"] = "checked"
        chunk["source_excerpt_role"] = "manual_confirmed_teaching_summary_not_verbatim"
        chunk["word_verification"] = "manual_teaching_summary_confirmed"
        review["review_status"] = "manual_confirmed"
    elif decision == "confirm_boundary_fragment":
        chunk["review_status"] = "checked"
        chunk["source_excerpt_role"] = "manual_confirmed_boundary_fragment_not_verbatim"
        chunk["word_verification"] = "manual_boundary_fragment_confirmed"
        review["review_status"] = "manual_confirmed"
    elif decision in {"split_required", "reject_candidate", "manual_anchor_pending"}:
        chunk["review_status"] = "needs_evidence_boundary_review"
        chunk["word_verification"] = decision
        review["review_status"] = decision


def unique_list(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results


def split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[;；|,，\n]", str(value)) if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
