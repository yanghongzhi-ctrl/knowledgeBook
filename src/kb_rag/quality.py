from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .loader import KnowledgePackage, write_json
from .retrieve import normalize


def ambiguous_qa_cases(package: KnowledgePackage) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in package.qa_cases:
        key = normalize(str(case.get("question") or ""))
        if key:
            grouped[key].append(case)

    results: list[dict[str, Any]] = []
    for key, cases in sorted(grouped.items()):
        targets = sorted(set(str(case.get("expected_answer_card") or "") for case in cases))
        if len(targets) > 1:
            results.append(
                {
                    "normalized_question": key,
                    "expected_answer_cards": targets,
                    "cases": [
                        {
                            "test_id": case.get("test_id"),
                            "question": case.get("question"),
                            "expected_answer_card": case.get("expected_answer_card"),
                        }
                        for case in cases
                    ],
                }
            )
    return results


def duplicate_canonical_questions(package: KnowledgePackage) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in package.answer_cards:
        key = normalize(str(card.get("canonical_question") or ""))
        if key:
            grouped[key].append(card)
    return [
        {
            "normalized_question": key,
            "answer_cards": [
                {
                    "answer_id": card.get("answer_id"),
                    "section_id": card.get("section_id"),
                    "canonical_question": card.get("canonical_question"),
                    "related_kps": card.get("related_kps"),
                }
                for card in cards
            ],
        }
        for key, cards in sorted(grouped.items())
        if len(cards) > 1
    ]


def write_quality_report(package: KnowledgePackage, output_path: str | Path) -> Path:
    report = {
        "ambiguous_qa_cases": ambiguous_qa_cases(package),
        "duplicate_canonical_questions": duplicate_canonical_questions(package),
    }
    output = Path(output_path)
    write_json(output, report)
    return output

