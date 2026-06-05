from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .loader import KnowledgePackage, write_json
from .render import render_answer
from .retrieve import AnswerRetriever, confidence, coverage


@dataclass
class EvalResult:
    total: int
    top1_hits: int
    top3_hits: int
    passed: int
    failures: list[dict[str, Any]]
    by_mode: dict[str, dict[str, int]]

    @property
    def top1_rate(self) -> float:
        return self.top1_hits / self.total if self.total else 0.0

    @property
    def top3_rate(self) -> float:
        return self.top3_hits / self.total if self.total else 0.0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def evaluate_package(package: KnowledgePackage, limit: int | None = None) -> EvalResult:
    retriever = AnswerRetriever(package)
    cases = package.qa_cases[:limit] if limit else package.qa_cases
    failures: list[dict[str, Any]] = []
    top1_hits = 0
    top3_hits = 0
    passed = 0
    by_mode: dict[str, dict[str, int]] = {}

    for case in cases:
        question = str(case.get("question", ""))
        expected = str(case.get("expected_answer_card", ""))
        mode = str(case.get("required_response_mode", ""))
        by_mode.setdefault(mode, {"total": 0, "passed": 0})
        by_mode[mode]["total"] += 1

        hits = retriever.search(question, top_k=5)
        actual = hits[0].answer_id if hits else ""
        hit_ids = [hit.answer_id for hit in hits]
        if actual == expected:
            top1_hits += 1
        if expected in hit_ids[:3]:
            top3_hits += 1

        answer = render_answer(hits[0].card, include_evidence=False) if hits else ""
        expected_points = case.get("expected_answer_points") or []
        should_not_include = case.get("should_not_include") or []
        point_coverage = coverage(expected_points, answer)
        unexpected = [item for item in should_not_include if str(item) and str(item) in answer]
        format_ok = _format_ok(mode, answer)
        case_passed = actual == expected and point_coverage >= 0.7 and not unexpected and format_ok

        if case_passed:
            passed += 1
            by_mode[mode]["passed"] += 1
        else:
            failures.append(
                {
                    "test_id": case.get("test_id"),
                    "question": question,
                    "expected_answer_card": expected,
                    "actual_answer_card": actual,
                    "top_ids": hit_ids,
                    "top_scores": [round(hit.score, 2) for hit in hits],
                    "top_reasons": [hit.reasons for hit in hits[:3]],
                    "confidence": confidence(hits[0].score) if hits else "none",
                    "point_coverage": round(point_coverage, 3),
                    "unexpected_content": unexpected,
                    "format_ok": format_ok,
                }
            )

    return EvalResult(
        total=len(cases),
        top1_hits=top1_hits,
        top3_hits=top3_hits,
        passed=passed,
        failures=failures,
        by_mode=by_mode,
    )


def write_eval_report(result: EvalResult, report_path: str | Path, failures_path: str | Path) -> None:
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RAG 自动评测报告",
        "",
        f"- 测试问题总数：{result.total}",
        f"- Top1 命中率：{result.top1_hits}/{result.total} = {result.top1_rate:.2%}",
        f"- Top3 命中率：{result.top3_hits}/{result.total} = {result.top3_rate:.2%}",
        f"- 通过率：{result.passed}/{result.total} = {result.pass_rate:.2%}",
        f"- 失败样例数：{len(result.failures)}",
        "",
        "## 按输出模式统计",
        "",
        "| 模式 | 通过 | 总数 | 通过率 |",
        "|---|---:|---:|---:|",
    ]
    for mode, stats in sorted(result.by_mode.items()):
        total = stats["total"]
        ok = stats["passed"]
        lines.append(f"| {mode or '未标注'} | {ok} | {total} | {(ok / total if total else 0):.2%} |")

    lines.extend(["", "## 失败样例 Top 20", ""])
    for failure in result.failures[:20]:
        lines.append(
            f"- `{failure['test_id']}` 期望 `{failure['expected_answer_card']}`，"
            f"实际 `{failure['actual_answer_card']}`，覆盖率 {failure['point_coverage']:.1%}："
            f"{failure['question']}"
        )

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(failures_path, result.failures)


def _format_ok(mode: str, answer: str) -> bool:
    if mode == "table":
        return "|" in answer and "---" in answer
    if mode == "step":
        return "步骤" in answer or "1." in answer
    if mode == "bullet":
        return "1." in answer
    return bool(answer.strip())
