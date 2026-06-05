from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = next((ROOT / "data/raw/ch03").glob("*.json"))


def main() -> None:
    data = json.loads(RAW.read_text(encoding="utf-8"))

    cards = data.setdefault("Answer_Cards", [])
    rag_config = data.setdefault("RAG_Config", [])
    embeddings = data.setdefault("Embedding_Corpus", [])
    synonyms = data.setdefault("Synonyms_Questions", [])
    qa_cases = data.setdefault("QA_Evaluation_Testset", [])

    by_id = {row.get("answer_id"): row for row in cards}
    _extend_patterns(
        by_id["ans_ch03_010"],
        [
            "平面CAD系统的功能",
            "平面CAD系统功能",
            "路线平面CAD系统功能有哪些？",
            "平面CAD有哪些功能？",
        ],
    )
    _extend_patterns(
        by_id["ans_ch03_014"],
        [
            "纵断面CAD系统功能",
            "纵断面CAD系统的功能",
            "纵断面CAD系统有哪些功能？",
            "纵断面CAD有哪些功能？",
        ],
    )
    _specialize_summary_flow_card(by_id["ans_ch03_067"])

    content_card = {
        "answer_id": "ans_ch03_181",
        "chapter_id": "ch03",
        "section_id": "ch03_sec02",
        "canonical_question": "平面CAD系统中人机分工的内容包括什么？",
        "question_type": "条目列举",
        "student_question_patterns": [
            "人机分工的内容",
            "平面CAD系统人机分工内容",
            "平面CAD系统中人和计算机分别承担什么工作？",
            "平面CAD中人负责什么、计算机负责什么？",
        ],
        "related_kps": ["kp_ch03_043"],
        "answer_mode": "bullet",
        "answer_points": [
            "人负责设计意图表达、方案判断、控制条件选择和交互修改。",
            "计算机负责几何计算、曲线与坐标计算、规范检查、图形更新和数据管理。",
            "交互界面负责把人工判断与自动计算连接起来，使修改、校核和出图形成闭环。",
        ],
        "concise_answer": "人负责设计意图、方案判断和控制条件选择；计算机负责几何计算、规范检查、图形更新和数据管理；交互界面把人工判断与自动计算连接成闭环。",
        "expanded_answer": "人负责设计意图表达、方案判断、控制条件选择和交互修改。计算机负责几何计算、曲线与坐标计算、规范检查、图形更新和数据管理。交互界面负责把人工判断与自动计算连接起来，使修改、校核和出图形成闭环。",
        "must_include": [
            "人负责设计意图表达、方案判断、控制条件选择和交互修改。",
            "计算机负责几何计算、曲线与坐标计算、规范检查、图形更新和数据管理。",
            "交互界面负责把人工判断与自动计算连接起来",
        ],
        "avoid_content": [
            "不要只回答抽象原则而不说明人和计算机分别承担的工作。",
            "不要扩展到第三章未涉及的软件实操细节。",
            "不要把证据片段作为答案主体。",
        ],
        "evidence_chunks": ["ch03_chunk_005"],
        "source_excerpt": "教材第三章在平面CAD系统设计部分说明了设计人员与计算机之间的任务分配关系。",
        "answer_boundary": "依据第三章道路CAD系统设计原理回答，重点区分人承担的工程判断与计算机承担的自动计算处理。",
        "recommended_resources": [],
        "confidence_rule": "命中Answer_Cards且包含must_include时为高置信度；仅命中Source_Chunks时不得直接生成长答案。",
        "status": "checked",
    }
    _upsert_by(cards, "answer_id", content_card)

    for answer_id in ("ans_ch03_010", "ans_ch03_014", "ans_ch03_181"):
        card = next(row for row in cards if row.get("answer_id") == answer_id)
        _upsert_by(rag_config, "config_id", _rag_row(card))
        _upsert_by(embeddings, "embedding_id", _embedding_row(card))

    synonym_rows = {
        "ans_ch03_010": [
            "平面CAD系统的功能",
            "平面CAD系统功能",
            "路线平面CAD系统功能有哪些？",
        ],
        "ans_ch03_014": [
            "纵断面CAD系统功能",
            "纵断面CAD系统的功能",
            "纵断面CAD系统有哪些功能？",
        ],
        "ans_ch03_181": [
            "人机分工的内容",
            "平面CAD系统人机分工内容",
            "平面CAD系统中人和计算机分别承担什么工作？",
            "平面CAD中人负责什么、计算机负责什么？",
        ],
    }
    for target_id, aliases in synonym_rows.items():
        card = next(row for row in cards if row.get("answer_id") == target_id)
        for alias in aliases:
            _upsert_by(synonyms, "synonym_id", _synonym_row(card, alias, target_id))

    qa_rows = [
        ("eval_ch03_disamb_001", "平面CAD系统的功能", "ans_ch03_010", ["完整的几何计算功能。"]),
        ("eval_ch03_disamb_002", "纵断面CAD系统功能", "ans_ch03_014", ["控制条件的查询与检查。"]),
        ("eval_ch03_disamb_003", "纵断面CAD系统的功能", "ans_ch03_014", ["控制条件的查询与检查。"]),
        ("eval_ch03_disamb_004", "人机分工的内容", "ans_ch03_181", ["人负责设计意图表达、方案判断、控制条件选择和交互修改。"]),
        ("eval_ch03_disamb_005", "平面CAD系统中人和计算机分别承担什么工作？", "ans_ch03_181", ["计算机负责几何计算、曲线与坐标计算、规范检查、图形更新和数据管理。"]),
        ("eval_ch03_disamb_006", "人机分工的原则", "ans_ch03_009", ["设计人员负责方案意图、控制条件选择和工程判断。"]),
    ]
    for test_id, question, expected, points in qa_rows:
        _upsert_by(qa_cases, "test_id", _qa_row(test_id, question, expected, points))

    RAW.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"patched={RAW}")
    print(f"answer_cards={len(cards)}")
    print(f"qa_cases={len(qa_cases)}")
    print(f"synonyms={len(synonyms)}")


def _extend_patterns(card: dict[str, Any], patterns: list[str]) -> None:
    existing = list(card.get("student_question_patterns") or [])
    seen = set(existing)
    for pattern in patterns:
        if pattern not in seen:
            existing.append(pattern)
            seen.add(pattern)
    card["student_question_patterns"] = existing


def _specialize_summary_flow_card(card: dict[str, Any]) -> None:
    card["canonical_question"] = "从概括性流程总结角度，传统路线平面设计流程是什么？"
    card["student_question_patterns"] = [
        "从概括性流程总结角度，传统路线平面设计流程是什么？",
        "请从概括性流程总结角度简要说明：传统路线平面设计流程是什么？",
        "请从概括性流程总结角度按条目回答：传统路线平面设计流程是什么？",
    ]


def _upsert_by(rows: list[dict[str, Any]], key: str, row: dict[str, Any]) -> None:
    row_key = row.get(key)
    for idx, item in enumerate(rows):
        if item.get(key) == row_key:
            rows[idx] = row
            return
    rows.append(row)


def _rag_row(card: dict[str, Any]) -> dict[str, Any]:
    answer_id = str(card["answer_id"])
    points = list(card.get("answer_points") or [])
    patterns = list(card.get("student_question_patterns") or [])
    index_text = "。".join([str(card.get("canonical_question", "")), "；".join(patterns), "；".join(points)])
    keywords = ";".join([str(card.get("canonical_question", "")), *patterns, *points])
    return {
        "config_id": f"rag_{answer_id}",
        "target_type": "answer_card",
        "target_id": answer_id,
        "retrieval_priority": 80 if answer_id == "ans_ch03_181" else 60,
        "retrieval_keywords": keywords,
        "embedding_text": index_text,
        "answer_mode": card.get("answer_mode") or "bullet",
        "need_citation": True,
        "allow_ai_extension": "limited",
        "rerank_weight": 1.0,
        "use_as_primary_answer": True,
        "chapter_id": "ch03",
        "object_id": answer_id,
        "object_type": "answer_card",
        "index_text": index_text,
    }


def _embedding_row(card: dict[str, Any]) -> dict[str, Any]:
    answer_id = str(card["answer_id"])
    text = f"{card.get('canonical_question', '')}。{'；'.join(card.get('student_question_patterns') or [])}。要点：{';'.join(card.get('answer_points') or [])}"
    return {
        "corpus_id": f"emb_{answer_id}",
        "object_type": "answer_card",
        "object_id": answer_id,
        "chapter_id": "ch03",
        "section_id": card.get("section_id") or "ch03_sec02",
        "embedding_text": text,
        "retrieval_priority": 80 if answer_id == "ans_ch03_181" else 60,
        "embedding_id": f"emb_{answer_id}",
        "source_type": "answer_card",
        "source_id": answer_id,
        "metadata": {
            "chapter_id": "ch03",
            "section_id": card.get("section_id") or "ch03_sec02",
            "priority": "P0",
        },
    }


def _synonym_row(card: dict[str, Any], alias: str, target_id: str) -> dict[str, Any]:
    digest = hashlib.sha1(f"{target_id}:{alias}".encode("utf-8")).hexdigest()[:10]
    return {
        "syn_id": f"syn_ch03_disamb_{digest}",
        "standard_id": target_id,
        "standard_term": card.get("canonical_question"),
        "alias_or_question": alias,
        "type": "student_question",
        "chapter_id": "ch03",
        "section_id": card.get("section_id") or "ch03_sec02",
        "priority": 5,
        "target_id": target_id,
        "synonym_id": f"syn_ch03_disamb_{digest}",
    }


def _qa_row(test_id: str, question: str, expected: str, points: list[str]) -> dict[str, Any]:
    return {
        "eval_id": test_id,
        "question": question,
        "expected_answer_card": expected,
        "must_include": points,
        "should_not_include": ["教材原文长段落", "无关软件操作细节", "超出第三章范围内容"],
        "expected_mode": "bullet_or_table",
        "pass_rule": "命中正确答案卡，包含必答点，输出条目化且不复制长段原文。",
        "status": "pending",
        "chapter_id": "ch03",
        "test_id": test_id,
        "expected_answer_points": points,
        "expected_kps": [],
        "required_response_mode": "bullet",
    }


if __name__ == "__main__":
    main()
