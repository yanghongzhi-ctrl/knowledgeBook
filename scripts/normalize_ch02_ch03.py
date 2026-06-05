from __future__ import annotations

import json
import hashlib
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(r"D:\道路工程数字设计方法\教材脚本")

CHAPTERS = {
    "ch02": {
        "raw": ROOT / "data/raw/ch02/第2章_道路建模的图形原理与三维表达_知识库_v1.0完备版.json",
        "title": "道路建模的图形原理与三维表达",
        "patterns": ["2.*.html"],
    },
    "ch03": {
        "raw": ROOT / "data/raw/ch03/第3章_道路CAD系统的设计原理_知识库_v1.0完备版.json",
        "title": "道路CAD系统的设计原理",
        "patterns": ["3.*.html"],
    },
}

TABLE_MAP = {
    "metadata": "README",
    "chapter_structure": "Chapter_Structure",
    "source_chunks": "Source_Chunks",
    "knowledge_points": "Knowledge_Points",
    "answer_cards": "Answer_Cards",
    "concept_comparison": "Concept_Comparison",
    "synonyms": "Synonyms_Questions",
    "Synonyms": "Synonyms_Questions",
    "knowledge_relations": "Knowledge_Relations",
    "resources": "Resources",
    "exercises": "Exercises",
    "qa_testset": "QA_Testset",
    "qa_evaluation_testset": "QA_Evaluation_Testset",
    "rag_config": "RAG_Config",
    "embedding_corpus": "Embedding_Corpus",
    "question_routing_rules": "Question_Routing_Rules",
    "answer_policy": "Answer_Policies",
    "answer_policies": "Answer_Policies",
    "quality_checklist": "Quality_Checklist",
}

LIST_FIELDS = {
    "student_question_patterns",
    "related_kps",
    "answer_points",
    "must_include",
    "avoid_content",
    "evidence_chunks",
    "recommended_resources",
    "keywords",
    "aliases",
    "common_mistakes",
    "expected_kps",
    "expected_answer_points",
    "should_not_include",
    "standard_answer_points",
    "display_objects",
    "operation_steps",
    "trigger_questions",
    "extracted_labels",
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
]


def main() -> int:
    for chapter_id, config in CHAPTERS.items():
        normalize_chapter(chapter_id, config)
    return 0


def normalize_chapter(chapter_id: str, config: dict[str, Any]) -> None:
    path = Path(config["raw"])
    data = json.loads(path.read_text(encoding="utf-8"))
    normalized = _normalize_tables(data)
    _normalize_rows(normalized, chapter_id)
    _prefer_complete_qa_testset(normalized)
    _align_qa_modes_with_cards(normalized)
    _disambiguate_known_duplicate_questions(normalized, chapter_id)
    _copy_interactive_scripts(normalized, chapter_id, config["patterns"])
    _ensure_prompts(normalized, chapter_id)
    _ensure_required_tables(normalized)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"{chapter_id}: answers={len(normalized['Answer_Cards'])} "
        f"qa={len(normalized['QA_Evaluation_Testset'])} "
        f"resources={len(normalized['Resources'])} "
        f"scripts={len(normalized['Interactive_Scripts'])}"
    )


def _normalize_tables(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        mapped = TABLE_MAP.get(key, key)
        if mapped in result and isinstance(result[mapped], list) and isinstance(value, list):
            result[mapped].extend(value)
        else:
            result[mapped] = value
    return result


def _normalize_rows(data: dict[str, Any], chapter_id: str) -> None:
    for table, rows in list(data.items()):
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if table != "README" and row.get("chapter_id") in (None, ""):
                row["chapter_id"] = chapter_id
            for field in LIST_FIELDS:
                if field in row:
                    row[field] = _as_list(row[field])
            if table == "Resources":
                _normalize_resource(row, chapter_id)
            if table == "Synonyms_Questions":
                _normalize_synonym(row)
            if table == "Knowledge_Relations":
                _normalize_relation(row)
            if table == "RAG_Config":
                _normalize_rag_config(row)
            if table == "Embedding_Corpus":
                _normalize_embedding_corpus(row)
            if table == "Answer_Cards":
                _normalize_answer_card(row)
            if table == "Knowledge_Points":
                _normalize_knowledge_point(row)
            if table == "QA_Evaluation_Testset":
                _normalize_qa_case(row, chapter_id)
            if table == "Source_Chunks":
                row["usable_for_answer"] = "no_direct_output"


def _normalize_resource(row: dict[str, Any], chapter_id: str) -> None:
    resource_type = str(row.get("resource_type") or "")
    if resource_type == "figure":
        row["resource_type"] = "image"
    row.setdefault("chapter_id", chapter_id)
    row["related_kps"] = _as_list(row.get("related_kps"))
    row["keywords"] = _as_list(row.get("keywords"))
    title = str(row.get("title") or row.get("caption_or_name") or row.get("resource_id") or "")
    if title and not row.get("title"):
        row["title"] = title
    if not row["keywords"] and title:
        row["keywords"] = _keywords_from_title(title)
    if not row.get("status"):
        row["status"] = "placeholder"


def _normalize_synonym(row: dict[str, Any]) -> None:
    if "synonym_id" not in row and row.get("id"):
        row["synonym_id"] = row["id"]
    if not row.get("alias_or_question"):
        row["alias_or_question"] = _first_text(
            row,
            "alias",
            "question",
            "term",
            "text",
            "standard_term",
        )
    if not row.get("target_id") and row.get("answer_id"):
        row["target_id"] = row["answer_id"]
    if not row.get("target_id") and row.get("kp_id"):
        row["target_id"] = row["kp_id"]
    if not row.get("target_id") and row.get("standard_term"):
        row["target_id"] = row["standard_term"]
    if not row.get("standard_term"):
        row["standard_term"] = _first_text(row, "term", "alias_or_question", "target_id")
    if "type" not in row:
        row["type"] = "alias"
    if "priority" not in row:
        row["priority"] = 0
    if "synonym_id" not in row:
        target = str(row.get("target_id") or row.get("standard_term") or "target")
        alias = str(row.get("alias_or_question") or row.get("standard_term") or "alias")
        digest = hashlib.sha1(f"{target}|{alias}".encode("utf-8")).hexdigest()[:10]
        safe_target = re.sub(r"[^A-Za-z0-9_]+", "_", target).strip("_") or "target"
        row["synonym_id"] = f"syn_{safe_target}_{digest}"


def _normalize_relation(row: dict[str, Any]) -> None:
    if not row.get("source_id"):
        row["source_id"] = _first_text(row, "source_id", "source_kp", "source_answer", "source")
    if not row.get("target_id"):
        row["target_id"] = _first_text(row, "target_id", "target_kp", "target_answer", "target")
    if not row.get("relation_type"):
        row["relation_type"] = _first_text(row, "relation", "type") or "related"
    if "weight" not in row:
        row["weight"] = 1
    if "use_in_recommendation" not in row:
        row["use_in_recommendation"] = True
    if "use_in_rag" not in row:
        row["use_in_rag"] = False
    if "relation_id" not in row:
        source = str(row.get("source_id") or "source")
        target = str(row.get("target_id") or "target")
        relation = str(row.get("relation_type") or "related")
        digest = hashlib.sha1(f"{source}|{relation}|{target}".encode("utf-8")).hexdigest()[:10]
        row["relation_id"] = f"rel_{digest}"


def _first_text(row: dict[str, Any], *fields: str) -> str:
    for field in fields:
        value = row.get(field)
        if value is None:
            continue
        if isinstance(value, list):
            value = " ".join(str(item).strip() for item in value if str(item).strip())
        text = str(value).strip()
        if text:
            return text
    return ""


def _numeric_priority(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"-?\d+", str(value))
    return int(match.group(0)) if match else 0


def _normalize_rag_config(row: dict[str, Any]) -> None:
    if not row.get("object_id"):
        row["object_id"] = _first_text(row, "target_id", "answer_id", "kp_id", "resource_id", "config_id")
    if not row.get("object_type"):
        row["object_type"] = _first_text(row, "target_type", "type") or "answer_card"
    if isinstance(row.get("index_text"), list):
        row["index_text"] = " ".join(str(item) for item in row["index_text"])
    if not row.get("index_text"):
        row["index_text"] = _first_text(row, "embedding_text", "retrieval_keywords", "question", "title", "object_id")
    row["retrieval_priority"] = _numeric_priority(row.get("retrieval_priority"))


def _normalize_embedding_corpus(row: dict[str, Any]) -> None:
    if not row.get("embedding_id"):
        row["embedding_id"] = _first_text(row, "embed_id", "corpus_id", "id")
    if not row.get("source_type"):
        row["source_type"] = _first_text(row, "object_type", "target_type", "type") or "answer_card"
    if not row.get("source_id"):
        row["source_id"] = _first_text(row, "object_id", "target_id", "answer_id", "kp_id", "resource_id")
    source_embedding_text = _first_text(row, "text_for_embedding")
    if source_embedding_text:
        row["embedding_text"] = source_embedding_text
    elif not row.get("embedding_text"):
        row["embedding_text"] = _first_text(
            row,
            "text",
            "index_text",
            "retrieval_keywords",
            "source_id",
        )
    if not row.get("metadata"):
        meta = {
            "chapter_id": row.get("chapter_id"),
            "section_id": row.get("section_id"),
            "priority": row.get("priority") or row.get("retrieval_priority"),
        }
        row["metadata"] = {key: value for key, value in meta.items() if value not in (None, "")}
    if "priority" in row:
        row["priority"] = _numeric_priority(row.get("priority"))
    if "retrieval_priority" in row:
        row["retrieval_priority"] = _numeric_priority(row.get("retrieval_priority"))


def _normalize_answer_card(row: dict[str, Any]) -> None:
    row.setdefault("status", "checked")
    row["student_question_patterns"] = _as_list(row.get("student_question_patterns"))
    row["related_kps"] = _as_list(row.get("related_kps"))
    row["answer_points"] = _as_list(row.get("answer_points"))
    row["must_include"] = _as_list(row.get("must_include")) or _as_list(row.get("answer_points"))[:2]
    row["avoid_content"] = _as_list(row.get("avoid_content"))
    row["evidence_chunks"] = _as_list(row.get("evidence_chunks"))
    row["recommended_resources"] = _as_list(row.get("recommended_resources"))


def _normalize_knowledge_point(row: dict[str, Any]) -> None:
    row.setdefault("status", "checked")
    row["key_points"] = _as_list(row.get("key_points"))
    if not row["key_points"]:
        candidates = [
            row.get("definition"),
            row.get("core_explanation"),
            row.get("plain_explanation"),
            row.get("engineering_meaning"),
        ]
        row["key_points"] = [str(item).strip() for item in candidates if str(item or "").strip()][:4]
    row["keywords"] = _as_list(row.get("keywords"))
    row["aliases"] = _as_list(row.get("aliases"))
    row["related_kps"] = _as_list(row.get("related_kps"))
    row["common_mistakes"] = _as_list(row.get("common_mistakes"))


def _normalize_qa_case(row: dict[str, Any], chapter_id: str) -> None:
    if not row.get("test_id"):
        digest = hashlib.sha1(str(row.get("question") or "").encode("utf-8")).hexdigest()[:10]
        row["test_id"] = row.get("eval_id") or f"qa_{chapter_id}_{digest}"
    if not row.get("expected_answer_points"):
        row["expected_answer_points"] = _as_list(row.get("must_include"))
    else:
        row["expected_answer_points"] = _as_list(row.get("expected_answer_points"))
    row["expected_kps"] = _as_list(row.get("expected_kps"))
    row["should_not_include"] = _as_list(row.get("should_not_include"))
    if not row.get("required_response_mode"):
        row["required_response_mode"] = row.get("expected_mode") or "bullet"
    row.setdefault("pass_rule", "top1_and_expected_points")


def _prefer_complete_qa_testset(data: dict[str, Any]) -> None:
    qa_testset = data.get("QA_Testset")
    qa_eval = data.get("QA_Evaluation_Testset")
    if not isinstance(qa_testset, list) or not qa_testset:
        return
    if not isinstance(qa_eval, list) or not qa_eval:
        data["QA_Evaluation_Testset"] = qa_testset
        return
    qa_eval_complete = all(
        isinstance(row, dict)
        and row.get("test_id")
        and row.get("expected_answer_points")
        and row.get("required_response_mode")
        for row in qa_eval[: min(20, len(qa_eval))]
    )
    if not qa_eval_complete:
        data["QA_Evaluation_Testset"] = qa_testset
        for row in data["QA_Evaluation_Testset"]:
            if isinstance(row, dict):
                _normalize_qa_case(row, str(row.get("chapter_id") or ""))


def _align_qa_modes_with_cards(data: dict[str, Any]) -> None:
    cards = {
        str(row.get("answer_id")): row
        for row in data.get("Answer_Cards", [])
        if isinstance(row, dict) and row.get("answer_id")
    }
    for case in data.get("QA_Evaluation_Testset", []):
        if not isinstance(case, dict):
            continue
        card = cards.get(str(case.get("expected_answer_card") or ""))
        if card and card.get("answer_mode"):
            case["required_response_mode"] = card.get("answer_mode")
        if card and not case.get("expected_answer_points"):
            case["expected_answer_points"] = _as_list(card.get("must_include")) or _as_list(card.get("answer_points"))


def _disambiguate_known_duplicate_questions(data: dict[str, Any], chapter_id: str) -> None:
    replacements = {
        "ch02": {
            ("ans_ch02_130", "DTM和DEM有什么区别？"): "从信息范围、表达对象和应用场景角度，DTM与DEM比较如何比较？",
            ("ans_ch02_132", "WCS和UCS有什么区别？"): "从坐标范围、是否可自定义和建模作用角度，WCS与UCS比较如何比较？",
            ("ans_ch02_133", "地理坐标系和投影坐标系有什么区别？"): "从坐标形式、应用目的和工程计算角度，地理坐标系与投影坐标系比较如何比较？",
            ("ans_ch02_136", "正投影和透视投影有什么区别？"): "从尺寸真实性、视觉真实感和适用场景角度，正投影与透视投影比较如何比较？",
        },
        "ch03": {
            ("ans_ch03_067", "传统路线平面设计流程是什么？"): "从概括性流程总结角度，传统路线平面设计流程是什么？",
            ("ans_ch03_067", "请简要说明：传统路线平面设计流程是什么？"): "请从概括性流程总结角度简要说明：传统路线平面设计流程是什么？",
            ("ans_ch03_067", "请按条目回答：传统路线平面设计流程是什么？"): "请从概括性流程总结角度按条目回答：传统路线平面设计流程是什么？",
        },
    }.get(chapter_id, {})
    if not replacements:
        return

    cards = {
        str(row.get("answer_id")): row
        for row in data.get("Answer_Cards", [])
        if isinstance(row, dict) and row.get("answer_id")
    }
    for case in data.get("QA_Evaluation_Testset", []):
        if not isinstance(case, dict):
            continue
        key = (str(case.get("expected_answer_card") or ""), str(case.get("question") or ""))
        replacement = replacements.get(key)
        if not replacement:
            continue
        case["question"] = replacement
        card = cards.get(key[0])
        if card is not None:
            patterns = _as_list(card.get("student_question_patterns"))
            if replacement not in patterns:
                patterns.insert(0, replacement)
            card["student_question_patterns"] = patterns


def _copy_interactive_scripts(data: dict[str, Any], chapter_id: str, patterns: list[str]) -> None:
    asset_dir = ROOT / "assets" / chapter_id / "interactive_html"
    asset_dir.mkdir(parents=True, exist_ok=True)
    html_files: list[Path] = []
    for pattern in patterns:
        html_files.extend(SOURCE_ROOT.glob(pattern))
    html_files = sorted(set(html_files), key=lambda item: item.name)

    resources_by_id = {str(row.get("resource_id")): row for row in data.get("Resources", [])}
    scripts_by_id = {str(row.get("script_id")): row for row in data.get("Interactive_Scripts", [])}

    for html in html_files:
        shutil.copy2(html, asset_dir / html.name)
        section_no = _section_no(html.name)
        resource_id = f"{chapter_id}_script_{section_no.replace('.', '_')}"
        script_id = f"{chapter_id}_interactive_{section_no.replace('.', '_')}"
        title = _clean_html_title(html)
        file_path = (Path("assets") / chapter_id / "interactive_html" / html.name).as_posix()
        related_kps = _related_kps_for_section(data, chapter_id, section_no)
        trigger_questions = [
            f"{title}怎么看？",
            f"{title}怎么操作？",
            f"我想看{title}。",
        ]
        keywords = _keywords_from_title(title)

        resource = resources_by_id.get(resource_id)
        if resource is None:
            resource = {
                "resource_id": resource_id,
                "chapter_id": chapter_id,
                "section_id": f"{chapter_id}_sec{int(section_no.split('.')[1]):02d}" if "." in section_no else "",
                "resource_type": "interactive_html",
                "title": title,
                "description": f"用于辅助理解{title}相关知识点。",
                "related_kps": related_kps,
                "keywords": keywords,
                "teaching_use": "自学复习、课堂讲解参考和AI回答后的资源推荐",
                "qa_use": "当学习问题询问脚本、演示或操作方式时推荐",
                "status": "bound",
            }
            data.setdefault("Resources", []).append(resource)
            resources_by_id[resource_id] = resource
        resource.update(
            {
                "resource_type": "interactive_html",
                "file_path": file_path,
                "status": "bound",
                "trigger_questions": trigger_questions,
            }
        )
        resource["related_kps"] = _as_list(resource.get("related_kps")) or related_kps
        resource["keywords"] = _as_list(resource.get("keywords")) or keywords

        script = scripts_by_id.get(script_id)
        if script is None:
            script = {
                "script_id": script_id,
                "resource_id": resource_id,
                "chapter_id": chapter_id,
                "title": title,
                "file_path": file_path,
                "interaction_theme": title,
                "display_objects": keywords,
                "operation_steps": [
                    "打开互动脚本并观察主界面对象",
                    "按页面提示切换参数、图层或设计状态",
                    "对照教材知识点总结模型表达或CAD设计逻辑",
                ],
                "trigger_questions": trigger_questions,
                "related_kps": related_kps,
                "extracted_labels": keywords,
                "status": "bound",
            }
            data.setdefault("Interactive_Scripts", []).append(script)
            scripts_by_id[script_id] = script
        else:
            script.update({"resource_id": resource_id, "file_path": file_path, "status": "bound"})


def _ensure_prompts(data: dict[str, Any], chapter_id: str) -> None:
    prompts = data.get("Prompt_Templates")
    if isinstance(prompts, list) and prompts:
        return
    data["Prompt_Templates"] = [
        {
            "template_id": f"{chapter_id}_prompt_answer_card",
            "chapter_id": chapter_id,
            "name": "答案卡优先回答模板",
            "trigger": "answer_card",
            "template": "优先依据命中的答案卡组织回答；证据片段只作为依据，不直接长段输出。",
        },
        {
            "template_id": f"{chapter_id}_prompt_resource_guidance",
            "chapter_id": chapter_id,
            "name": "学习资源推荐模板",
            "trigger": "resource_guidance",
            "template": "当学习者询问图片、脚本、演示或操作方式时，优先推荐对应资源并给出查看要点。",
        },
    ]


def _ensure_required_tables(data: dict[str, Any]) -> None:
    for table in REQUIRED_LIST_TABLES:
        data.setdefault(table, [])


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    text = str(value)
    parts = [part.strip() for part in re.split(r"[;；]\s*", text) if part.strip()]
    return parts if len(parts) > 1 else ([text.strip()] if text.strip() else [])


def _section_no(filename: str) -> str:
    match = re.match(r"(\d+\.\d+)", filename)
    return match.group(1) if match else Path(filename).stem


def _clean_html_title(path: Path) -> str:
    name = path.stem.strip()
    title = re.sub(r"^\d+\.\d+[_\s]*", "", name).strip()
    return title or name


def _keywords_from_title(title: str) -> list[str]:
    clean = re.sub(r"[（）()《》:：,_，、\-—]+", " ", title)
    tokens = [item.strip() for item in clean.split() if item.strip()]
    if not tokens:
        tokens = [title]
    extras = re.findall(r"[A-Za-z][A-Za-z0-9+_-]*", title)
    result: list[str] = []
    for item in tokens + extras:
        if item and item not in result:
            result.append(item)
    return result[:8]


def _related_kps_for_section(data: dict[str, Any], chapter_id: str, section_no: str) -> list[str]:
    section_id = f"{chapter_id}_sec{int(section_no.split('.')[1]):02d}" if "." in section_no else ""
    kps = [
        str(row.get("kp_id"))
        for row in data.get("Knowledge_Points", [])
        if isinstance(row, dict) and row.get("section_id") == section_id and row.get("kp_id")
    ]
    return kps[:8]


if __name__ == "__main__":
    raise SystemExit(main())
