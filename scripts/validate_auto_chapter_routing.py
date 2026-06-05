from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from kb_rag.api import ApiState, normalize, route_chapter
from kb_rag.loader import load_package


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate automatic chapter routing across all loaded chapters.")
    parser.add_argument("--raw-dir", default=str(ROOT / "data/raw"))
    parser.add_argument("--source", choices=("canonical", "patterns", "all"), default="canonical")
    parser.add_argument("--max-failures", type=int, default=50)
    args = parser.parse_args()

    states = load_states(Path(args.raw_dir))
    cases = collect_cases(states, source=args.source)
    counts = Counter(case["question_key"] for case in cases)
    unique_cases = [case for case in cases if counts[case["question_key"]] == 1]
    duplicate_rows = len(cases) - len(unique_cases)

    failures: list[dict[str, Any]] = []
    checks = 0
    for case in unique_cases:
        for current_chapter, preferred_state in states.items():
            selected_state, routing = route_chapter(states, preferred_state, str(case["question"]))
            checks += 1
            if selected_state.chapter_id != case["expected_chapter"]:
                failures.append(
                    {
                        "current_chapter": current_chapter,
                        "expected_chapter": case["expected_chapter"],
                        "resolved_chapter": selected_state.chapter_id,
                        "answer_id": case["answer_id"],
                        "source": case["source"],
                        "question": case["question"],
                        "decision": routing.get("decision"),
                        "best_score": routing.get("best_score"),
                        "preferred_score": routing.get("preferred_score"),
                    }
                )
                if len(failures) >= args.max_failures:
                    break
        if len(failures) >= args.max_failures:
            break

    summary = {
        "chapters": sorted(states),
        "source": args.source,
        "cases": len(cases),
        "unique_cases": len(unique_cases),
        "duplicate_rows_skipped": duplicate_rows,
        "checks": checks,
        "failures": len(failures),
        "failure_samples": failures,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failures else 0


def load_states(raw_dir: Path) -> dict[str, ApiState]:
    states: dict[str, ApiState] = {}
    for package_path in sorted(raw_dir.glob("ch*/*.json")):
        state = ApiState(load_package(package_path))
        states[state.chapter_id] = state
    if not states:
        raise SystemExit(f"No chapter packages found under {raw_dir}")
    return states


def collect_cases(states: dict[str, ApiState], source: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    include_canonical = source in {"canonical", "all"}
    include_patterns = source in {"patterns", "all"}

    for chapter_id, state in sorted(states.items()):
        for card in state.package.answer_cards:
            answer_id = str(card.get("answer_id") or "")
            if include_canonical:
                question = str(card.get("canonical_question") or "").strip()
                if question:
                    cases.append(
                        {
                            "expected_chapter": chapter_id,
                            "answer_id": answer_id,
                            "source": "canonical",
                        "question": question,
                        "question_key": routing_case_key(question),
                    }
                )
            if include_patterns:
                for pattern in card.get("student_question_patterns", []) or []:
                    question = str(pattern or "").strip()
                    if question:
                        cases.append(
                            {
                                "expected_chapter": chapter_id,
                                "answer_id": answer_id,
                                "source": "student_pattern",
                            "question": question,
                            "question_key": routing_case_key(question),
                        }
                    )
    return cases


def routing_case_key(question: str) -> str:
    key = normalize(question)
    for prefix in ("什么是", "何为", "如何理解"):
        if key.startswith(prefix):
            key = key[len(prefix) :]
            break
    for suffix in ("是什么", "什么意思"):
        if key.endswith(suffix):
            key = key[: -len(suffix)]
            break
    return key or normalize(question)


if __name__ == "__main__":
    raise SystemExit(main())
