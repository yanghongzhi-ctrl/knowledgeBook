from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"
CH01_RAW = ROOT / "data" / "raw" / "ch01"
REPORT_JSON = ROOT / "output" / "ch01_v12_integration_report_2026-06-06.json"
REPORT_MD = ROOT / "output" / "ch01_v12_integration_report_2026-06-06.md"

EXTRA_TABLES = [
    "README_v1.2",
    "Core_Answer_Cards_30",
    "Canonical_QA_Pairs",
    "Negative_Constraints",
    "Routing_Config",
    "QA_Retrieval_Testset_v1.2",
    "Retrieval_Test_Results",
    "Answer_Quality_Check",
    "QA_Failure_Revision_v1.2",
    "OpenSource_Index_Input_v1.2",
    "RAG_Config_v1.2",
    "Embedding_Corpus_v1.2",
    "Pipeline_Status_v1.2",
    "Validation_Summary_v1.2",
]

SCOPED_PATTERN_OWNERS = {
    "构件化理念是什么？": "ans_ch01_065",
    "构件化理念怎么理解？": "ans_ch01_065",
    "请解释构件化理念": "ans_ch01_065",
    "参数化理念是什么？": "ans_ch01_068",
    "参数化理念怎么理解？": "ans_ch01_068",
    "请解释参数化理念": "ans_ch01_068",
    "协同化理念是什么？": "ans_ch01_071",
    "协同化理念怎么理解？": "ans_ch01_071",
    "请解释协同化理念": "ans_ch01_071",
    "生命周期化理念是什么？": "ans_ch01_074",
    "生命周期化理念怎么理解？": "ans_ch01_074",
    "请解释生命周期化理念": "ans_ch01_074",
    "请用教材观点说明数字孪生虚实闭环。": "ans_ch01_013",
    "规则—模型—数据路径是什么？": "ans_ch01_085",
    "传统道路设计流程短板是什么？": "ans_ch01_087",
    "传统道路设计流程短板怎么理解？": "ans_ch01_087",
    "模型驱动成果输出是什么？": "ans_ch01_095",
}

SECONDARY_SYNONYM_TARGETS = {
    ("构件化理念是什么？", "ans_ch01_016"),
    ("参数化理念是什么？", "ans_ch01_017"),
    ("协同化理念是什么？", "ans_ch01_018"),
    ("生命周期化理念是什么？", "ans_ch01_019"),
}

KEEP_CURRENT_TABLES = {
    "Resources",
    "Interactive_Scripts",
    "Resource_Evaluation_Testset",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Selectively integrate uploaded chapter 1 v1.2 calibration files.")
    parser.add_argument("--current", type=Path, default=next(CH01_RAW.glob("*.json")))
    parser.add_argument("--v12", type=Path, default=find_v12_package())
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report-json", type=Path, default=REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=REPORT_MD)
    args = parser.parse_args()

    current = json.loads(args.current.read_text(encoding="utf-8"))
    v12 = json.loads(args.v12.read_text(encoding="utf-8"))
    merged, report = integrate(current, v12, args.current, args.v12)

    output = args.output or args.current
    output.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"output={output}")
    print(f"report={args.report_json}")
    return 0


def find_v12_package() -> Path:
    ch01 = "\u7b2c1\u7ae0"
    title = "\u9053\u8def\u5de5\u7a0b\u6570\u5b57\u5316\u8bbe\u8ba1\u6982\u8ff0"
    kb = "\u77e5\u8bc6\u5e93"
    matches = sorted(
        (
            path
            for path in DOWNLOADS.glob("*v1.2*精准问答校准版.json")
            if ch01 in path.name and title in path.name and kb in path.name
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise SystemExit("Cannot find uploaded chapter 1 v1.2 package under Downloads.")
    return matches[0]


def integrate(current: dict[str, Any], v12: dict[str, Any], current_path: Path, v12_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    data = json.loads(json.dumps(current, ensure_ascii=False))
    report: dict[str, Any] = {
        "current_package": str(current_path),
        "v12_package": str(v12_path),
        "policy": "Selective integration: preserve released resources/scripts, merge v1.2 retrieval calibration and teaching-answer metadata.",
        "actions": [],
    }

    new_kps = merge_new_knowledge_points(data, v12)
    report["actions"].append({"action": "merge_new_knowledge_points", "count": len(new_kps), "ids": new_kps})

    answer_report = merge_answer_card_calibration(data, v12)
    report["actions"].append({"action": "merge_answer_card_calibration", **answer_report})

    cqa_report = merge_canonical_qa_as_synonyms(data, v12)
    report["actions"].append({"action": "merge_canonical_qa_as_synonyms", **cqa_report})

    rag_report = merge_rag_and_embedding_for_new_kps(data, v12)
    report["actions"].append({"action": "merge_rag_embedding_for_new_kps", **rag_report})

    guardrail_report = merge_negative_constraints(data, v12)
    report["actions"].append({"action": "merge_negative_constraints", **guardrail_report})

    extra_report = copy_extra_tables(data, v12)
    report["actions"].append({"action": "copy_v12_extra_tables", **extra_report})

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    metadata["ch01_v12_integration"] = {
        "source_package": str(v12_path),
        "integrated_at": "2026-06-06",
        "mode": "selective_calibration_merge",
        "preserved_tables": sorted(KEEP_CURRENT_TABLES),
        "notes": "v1.2 content is used as retrieval calibration and teaching rewrite support; current resources and interactive scripts are preserved.",
    }
    data["metadata"] = metadata

    report["summary"] = summarize(data, report)
    return data, report


def merge_new_knowledge_points(data: dict[str, Any], v12: dict[str, Any]) -> list[str]:
    existing = {str(row.get("kp_id")) for row in data.get("Knowledge_Points", []) if isinstance(row, dict)}
    added = []
    for row in v12.get("Knowledge_Points", []):
        if not isinstance(row, dict):
            continue
        kp_id = str(row.get("kp_id") or "")
        if not kp_id or kp_id in existing:
            continue
        candidate = json.loads(json.dumps(row, ensure_ascii=False))
        candidate["teaching_rewrite_supported"] = True
        candidate["word_alignment"] = {
            "support_type": "teaching_rewrite_supported_by_word_theme",
            "evidence_confidence": "medium",
            "not_verbatim_quote": True,
            "needs_textbook_anchor_review": False,
        }
        data.setdefault("Knowledge_Points", []).append(candidate)
        existing.add(kp_id)
        added.append(kp_id)
    return added


def merge_answer_card_calibration(data: dict[str, Any], v12: dict[str, Any]) -> dict[str, Any]:
    v12_by_id = {str(row.get("answer_id")): row for row in v12.get("Answer_Cards", []) if isinstance(row, dict) and row.get("answer_id")}
    core_ids = {
        str(row.get("answer_id"))
        for row in v12.get("Core_Answer_Cards_30", [])
        if isinstance(row, dict) and row.get("answer_id")
    }
    changed = []
    pattern_added = 0
    pattern_removed = 0
    for card in data.get("Answer_Cards", []):
        if not isinstance(card, dict):
            continue
        answer_id = str(card.get("answer_id") or "")
        source = v12_by_id.get(answer_id)
        if not source:
            continue
        original_patterns = list(card.get("student_question_patterns") or [])
        merged_patterns = merge_patterns(answer_id, original_patterns, source.get("student_question_patterns") or [])
        pattern_added += max(0, len(merged_patterns) - len(dedupe(original_patterns)))
        pattern_removed += max(0, len(dedupe(original_patterns)) - len(merged_patterns))
        card["student_question_patterns"] = merged_patterns
        for field in (
            "short_answer",
            "standard_answer",
            "card_level",
            "retrieval_weight_v1_2",
            "priority_v1_2",
            "source_chunks_role",
            "negative_constraints",
            "calibration_status",
        ):
            if field in source:
                card[field] = source[field]
        if answer_id in core_ids:
            card["teaching_rewrite_supported"] = True
            card["word_alignment"] = {
                "support_type": "teaching_rewrite_supported_by_word_theme",
                "evidence_confidence": "medium",
                "not_verbatim_quote": True,
                "needs_textbook_anchor_review": False,
                "source": "ch01_v12_core_answer_cards",
            }
        if source.get("avoid_content"):
            card["avoid_content"] = dedupe(list(card.get("avoid_content") or []) + list(source.get("avoid_content") or []))
        changed.append(answer_id)
    return {
        "cards_touched": len(changed),
        "pattern_added_net": pattern_added,
        "pattern_removed_net": pattern_removed,
        "core_cards_marked": len(core_ids),
    }


def merge_patterns(answer_id: str, current_patterns: list[Any], v12_patterns: list[Any]) -> list[str]:
    values = [str(item).strip() for item in current_patterns if str(item).strip()]
    for item in v12_patterns:
        text = str(item).strip()
        if not text:
            continue
        owner = SCOPED_PATTERN_OWNERS.get(text)
        if owner and owner != answer_id:
            continue
        values.append(text)
    values = [
        text
        for text in values
        if not (SCOPED_PATTERN_OWNERS.get(text) and SCOPED_PATTERN_OWNERS[text] != answer_id)
    ]
    return dedupe(values)


def merge_canonical_qa_as_synonyms(data: dict[str, Any], v12: dict[str, Any]) -> dict[str, Any]:
    answer_ids = {str(row.get("answer_id")) for row in data.get("Answer_Cards", []) if isinstance(row, dict)}
    existing_keys = {
        (compact(row.get("alias_or_question")), str(row.get("target_id") or ""))
        for row in data.get("Synonyms_Questions", [])
        if isinstance(row, dict)
    }
    added = []
    skipped_conflict = []
    for row in v12.get("Canonical_QA_Pairs", []):
        if not isinstance(row, dict):
            continue
        question = str(row.get("question") or "").strip()
        answer_id = str(row.get("answer_id") or "").strip()
        if not question or answer_id not in answer_ids:
            continue
        owner = SCOPED_PATTERN_OWNERS.get(question)
        if owner and owner != answer_id and (question, answer_id) not in SECONDARY_SYNONYM_TARGETS:
            skipped_conflict.append({"question": question, "answer_id": answer_id, "owner": owner})
            continue
        key = (compact(question), answer_id)
        if key in existing_keys:
            continue
        synonym = {
            "synonym_id": f"syn_ch01_v12_{len(added) + 1:04d}",
            "standard_term": row.get("qa_id") or answer_id,
            "alias_or_question": question,
            "type": f"v1.2_canonical_{row.get('question_intent') or 'qa'}",
            "target_id": answer_id,
            "priority": priority_value(row.get("priority")),
            "source": "Canonical_QA_Pairs_v1.2",
            "status": "checked",
        }
        data.setdefault("Synonyms_Questions", []).append(synonym)
        existing_keys.add(key)
        added.append(synonym["synonym_id"])
    return {"added": len(added), "skipped_conflict": len(skipped_conflict), "conflict_samples": skipped_conflict[:12]}


def merge_rag_and_embedding_for_new_kps(data: dict[str, Any], v12: dict[str, Any]) -> dict[str, Any]:
    kp_ids = {str(row.get("kp_id")) for row in data.get("Knowledge_Points", []) if isinstance(row, dict)}
    rag_ids = {str(row.get("object_id")) for row in data.get("RAG_Config", []) if isinstance(row, dict)}
    emb_ids = {str(row.get("embedding_id")) for row in data.get("Embedding_Corpus", []) if isinstance(row, dict)}
    rag_added = []
    emb_added = []
    for row in v12.get("RAG_Config", []):
        if not isinstance(row, dict):
            continue
        object_id = str(row.get("object_id") or "")
        if object_id in kp_ids and object_id not in rag_ids:
            candidate = json.loads(json.dumps(row, ensure_ascii=False))
            candidate["source"] = "ch01_v12_integration"
            data.setdefault("RAG_Config", []).append(candidate)
            rag_ids.add(object_id)
            rag_added.append(object_id)
    for row in v12.get("Embedding_Corpus", []):
        if not isinstance(row, dict):
            continue
        embedding_id = str(row.get("embedding_id") or "")
        source_id = str(row.get("source_id") or "")
        if source_id in kp_ids and embedding_id not in emb_ids:
            candidate = json.loads(json.dumps(row, ensure_ascii=False))
            candidate["source"] = "ch01_v12_integration"
            data.setdefault("Embedding_Corpus", []).append(candidate)
            emb_ids.add(embedding_id)
            emb_added.append(embedding_id)
    return {"rag_added": len(rag_added), "embedding_added": len(emb_added), "rag_ids": rag_added, "embedding_ids": emb_added}


def merge_negative_constraints(data: dict[str, Any], v12: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in v12.get("Negative_Constraints", []) if isinstance(row, dict)]
    data["Negative_Constraints"] = rows
    guardrails = data.setdefault("Answer_Guardrails", [])
    existing = {str(row.get("guardrail_id") or row.get("constraint_id") or "") for row in guardrails if isinstance(row, dict)}
    added = []
    for row in rows:
        guardrail_id = f"guardrail_{row.get('constraint_id')}"
        if guardrail_id in existing:
            continue
        guardrails.append(
            {
                "guardrail_id": guardrail_id,
                "chapter_id": "ch01",
                "title": row.get("scope") or row.get("constraint_id"),
                "rule": row.get("constraint"),
                "trigger": row.get("trigger"),
                "enforcement": row.get("enforcement"),
                "severity": "medium",
                "source": "Negative_Constraints_v1.2",
                "status": "checked",
            }
        )
        added.append(guardrail_id)
    return {"negative_constraints": len(rows), "answer_guardrails_added": len(added)}


def copy_extra_tables(data: dict[str, Any], v12: dict[str, Any]) -> dict[str, Any]:
    copied = []
    for table in EXTRA_TABLES:
        if table in v12:
            data[table] = v12[table]
            copied.append(table)
    for table in KEEP_CURRENT_TABLES:
        if table in v12:
            # Deliberately keep the released current table.
            continue
    return {"copied": copied, "count": len(copied), "preserved": sorted(KEEP_CURRENT_TABLES)}


def summarize(data: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    canonical_counts = Counter(compact(row.get("canonical_question")) for row in data.get("Answer_Cards", []) if isinstance(row, dict))
    duplicate_canonical = [key for key, count in canonical_counts.items() if key and count > 1]
    pattern_targets: dict[str, set[str]] = defaultdict(set)
    for row in data.get("Answer_Cards", []):
        if not isinstance(row, dict):
            continue
        answer_id = str(row.get("answer_id") or "")
        for pattern in row.get("student_question_patterns") or []:
            pattern_targets[compact(pattern)].add(answer_id)
    duplicate_patterns = {key: sorted(value) for key, value in pattern_targets.items() if key and len(value) > 1}
    return {
        "answer_cards": len(data.get("Answer_Cards", [])),
        "knowledge_points": len(data.get("Knowledge_Points", [])),
        "synonyms_questions": len(data.get("Synonyms_Questions", [])),
        "resources": len(data.get("Resources", [])),
        "interactive_scripts": len(data.get("Interactive_Scripts", [])),
        "duplicate_canonical": len(duplicate_canonical),
        "duplicate_student_patterns": len(duplicate_patterns),
        "duplicate_student_pattern_samples": list(duplicate_patterns.items())[:12],
        "actions": [action["action"] for action in report["actions"]],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Chapter 1 v1.2 Selective Integration Report",
        "",
        f"- Current package: `{report['current_package']}`",
        f"- v1.2 package: `{report['v12_package']}`",
        f"- Policy: {report['policy']}",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["", "## Actions", ""])
    for action in report["actions"]:
        lines.append(f"- `{action['action']}`: {json.dumps({k: v for k, v in action.items() if k != 'action'}, ensure_ascii=False)}")
    return "\n".join(lines).rstrip() + "\n"


def priority_value(value: Any) -> int:
    text = str(value or "").lower()
    if text == "highest":
        return 10
    if text == "high":
        return 8
    if text == "checked":
        return 5
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else 4


def dedupe(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value).strip()
        key = compact(text)
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result


def compact(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


if __name__ == "__main__":
    raise SystemExit(main())
