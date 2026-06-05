from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "web" / "question-bank.json"

CATEGORIES = ["核心概念", "系统功能", "设计流程", "易混辨析", "资源学习"]
CHAPTERS = {
    "ch01": {"title": "数字化设计概述"},
    "ch02": {"title": "图形原理与三维表达"},
    "ch03": {"title": "道路CAD系统设计原理"},
    "ch04": {"title": "道路BIM正向设计"},
    "ch05": {"title": "GIS理论与空间分析"},
    "ch06": {"title": "AutoCAD平台功能与使用方法"},
    "ch07": {"title": "道路CAD软件的使用"},
    "ch08": {"title": "道路BIM软件的使用"},
    "ch09": {"title": "BIM_GIS集成方法"},
    "ch10": {"title": "AI驱动的道路设计方法"},
    "ch11": {"title": "道路数字孪生的概念与方法体系"},
}

PINNED = {
    "ch01": [
        "道路工程数字化设计经历了哪些主要阶段？",
        "CAD图元和BIM构件有什么本质区别？",
        "数字孪生为什么强调虚实闭环？",
        "道路设计数字化演进时间轴怎么看？",
    ],
    "ch02": [
        "图形表达在道路建模中的作用是什么？",
        "WCS和UCS有什么区别？",
        "我想看表2-1。",
        "表2-1对比了什么？",
    ],
    "ch03": [
        "平面CAD系统的功能",
        "纵断面CAD系统功能",
        "人机分工的内容",
        "人机分工的原则",
    ],
    "ch04": [
        "BIM的定义和三大核心要素是什么？",
        "道路BIM正向设计的核心含义是什么？",
        "道路BIM正向设计流程包括哪五个环节？",
        "BIM成果交付为什么要采用开放格式？",
        "我想看道路BIM与建筑BIM。",
        "我想看BIM中的参数-规则-结果机制_PPR。",
    ],
    "ch05": [
        "什么是GIS的定义？",
        "什么是地图投影？",
        "什么是拓扑关系？",
        "什么是缓冲区分析？",
        "什么是道路网络分析？",
        "我想看空间数据模型、拓扑结构与BIM模型差异。",
    ],
}

PINNED_TARGETS = {
    ("ch01", "数字孪生为什么强调虚实闭环？"): ("answer_card", "ans_ch01_013"),
}

PREFIX_RE = re.compile(r"^(请)?(简要说明|按条目回答|查看)?[：:]\s*")


def main() -> None:
    bank = {"version": "2026-06-03", "categories": CATEGORIES, "chapters": {}}
    for chapter_id, chapter_meta in CHAPTERS.items():
        questions = build_chapter(chapter_id)
        bank["chapters"][chapter_id] = {"title": chapter_meta["title"], "questions": questions}
    OUTPUT.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"out={OUTPUT}")
    for chapter_id, payload in bank["chapters"].items():
        print(f"{chapter_id}: {len(payload['questions'])}")


def build_chapter(chapter_id: str) -> list[dict[str, Any]]:
    base = PROCESSED / chapter_id
    answer_cards = read_json(base / "answer_cards.json")
    resources = read_json(base / "resource_index.json")
    qa_cases = read_json(base / "qa_evaluation_testset.json")
    resource_cases = read_json(base / "resource_evaluation_testset.json")

    qa_by_answer = group_cases(qa_cases, "expected_answer_card")
    resource_cases_by_id = group_resource_cases(resource_cases)
    card_by_id = {str(card.get("answer_id")): card for card in answer_cards if card.get("answer_id")}
    resource_by_id = {str(item.get("resource_id")): item for item in resources if item.get("resource_id")}

    rows: list[dict[str, Any]] = []
    seen_questions: set[str] = set()
    seen_targets: set[tuple[str, str]] = set()

    for pinned in PINNED.get(chapter_id, []):
        target_type, target_id = PINNED_TARGETS.get((chapter_id, pinned), find_target(pinned, qa_cases, resource_cases))
        if target_type == "answer_card" and target_id in card_by_id:
            add_row(rows, seen_questions, seen_targets, chapter_id, pinned, "answer_card", target_id, True)
        elif target_type == "resource" and target_id in resource_by_id:
            add_row(rows, seen_questions, seen_targets, chapter_id, pinned, "resource", target_id, True)
        else:
            add_row(rows, seen_questions, seen_targets, chapter_id, pinned, "answer_card", "", True)

    for card in answer_cards:
        answer_id = str(card.get("answer_id") or "")
        if not answer_id:
            continue
        question = best_answer_question(card, qa_by_answer.get(answer_id, []))
        add_row(rows, seen_questions, seen_targets, chapter_id, question, "answer_card", answer_id, False)

    for resource in resources:
        resource_id = str(resource.get("resource_id") or "")
        if not resource_id:
            continue
        question = best_resource_question(resource, resource_cases_by_id.get(resource_id, []))
        add_row(rows, seen_questions, seen_targets, chapter_id, question, "resource", resource_id, False)

    rows.sort(key=sort_key)
    for index, row in enumerate(rows, 1):
        row["id"] = f"{chapter_id}_qb_{index:03d}"
    return rows


def add_row(
    rows: list[dict[str, Any]],
    seen_questions: set[str],
    seen_targets: set[tuple[str, str]],
    chapter_id: str,
    question: str,
    target_type: str,
    target_id: str,
    pinned: bool,
) -> None:
    question = clean_question(question)
    if not question:
        return
    question_key = normalize_question(question)
    target_key = (target_type, target_id)
    if question_key in seen_questions:
        return
    if target_id and target_key in seen_targets:
        return
        rows[:] = [row for row in rows if (row["target_type"], row["target_id"]) != target_key]
    seen_questions.add(question_key)
    if target_id:
        seen_targets.add(target_key)
    rows.append(
        {
            "id": "",
            "chapter_id": chapter_id,
            "category": "资源学习" if target_type == "resource" else category_for(question),
            "question": question,
            "target_type": target_type,
            "target_id": target_id,
            "source": "resource_index" if target_type == "resource" else "answer_cards",
            "pinned": pinned,
        }
    )


def best_answer_question(card: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    canonical = clean_question(str(card.get("canonical_question") or ""))
    if canonical:
        return canonical
    for case in cases:
        question = clean_question(str(case.get("question") or ""))
        if question:
            return question
    return ""


def best_resource_question(resource: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    best_case = sorted(cases, key=lambda row: resource_question_rank(str(row.get("question") or "")))
    for case in best_case:
        question = clean_question(str(case.get("question") or ""))
        if question:
            return question
    label = resource_label(resource)
    if label:
        return f"我想看{label}。"
    return ""


def resource_question_rank(question: str) -> tuple[int, int]:
    question = clean_question(question)
    if "我想看" in question:
        return (0, len(question))
    if "说明了什么" in question and "：" not in question and ":" not in question:
        return (1, len(question))
    if "怎么看" in question or "怎么操作" in question:
        return (2, len(question))
    return (3, len(question))


def resource_label(resource: dict[str, Any]) -> str:
    title = str(resource.get("title") or "").strip()
    match = re.search(r"(图|表|公式)\s*\d+[-－]\d+", title)
    if match:
        return match.group(0).replace(" ", "")
    resource_id = str(resource.get("resource_id") or "")
    match = re.search(r"(\d+)_(\d+)", resource_id)
    if match:
        prefix = "图" if "fig" in resource_id else "表" if "table" in resource_id else "公式" if "formula" in resource_id else ""
        if prefix:
            return f"{prefix}{match.group(1)}-{match.group(2)}"
    return title or resource_id


def find_target(question: str, qa_cases: list[dict[str, Any]], resource_cases: list[dict[str, Any]]) -> tuple[str, str]:
    key = normalize_question(question)
    for case in qa_cases:
        if normalize_question(str(case.get("question") or "")) == key:
            return "answer_card", str(case.get("expected_answer_card") or "")
    for case in resource_cases:
        if normalize_question(str(case.get("question") or "")) == key:
            return "resource", str(case.get("expected_resource_id") or case.get("expected_resource") or "")
    return "", ""


def group_cases(cases: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        value = str(case.get(key) or "")
        if value:
            grouped.setdefault(value, []).append(case)
    return grouped


def group_resource_cases(cases: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        value = str(case.get("expected_resource_id") or case.get("expected_resource") or "")
        if value:
            grouped.setdefault(value, []).append(case)
    return grouped


def category_for(question: str) -> str:
    if any(term in question for term in ("区别", "对比", "关系", "辨析", "原则", "内容", "为什么")):
        return "易混辨析"
    if any(term in question for term in ("流程", "步骤", "阶段", "方法", "如何", "怎么", "计算", "设计过程")):
        return "设计流程"
    if any(term in question for term in ("功能", "模块", "组成", "作用", "系统", "具备", "任务")):
        return "系统功能"
    return "核心概念"


def sort_key(row: dict[str, Any]) -> tuple[int, int, list[Any]]:
    category_index = CATEGORIES.index(row["category"]) if row["category"] in CATEGORIES else len(CATEGORIES)
    return (0 if row.get("pinned") else 1, category_index, natural_key(row["question"]))


def natural_key(text: str) -> list[Any]:
    parts = re.split(r"(\d+)", text)
    return [int(part) if part.isdigit() else part for part in parts]


def clean_question(question: str) -> str:
    question = PREFIX_RE.sub("", question.strip())
    question = question.replace("请查看", "").strip()
    return question


def normalize_question(question: str) -> str:
    question = clean_question(question).lower()
    question = re.sub(r"[\s。？?！!：:，,、；;“”\"'（）()\[\]【】—-]+", "", question)
    return question


def read_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
