from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .api import ApiState, answer_payload
from .loader import KnowledgePackage, write_json


@dataclass
class ResourceEvalResult:
    total: int
    top1_hits: int
    passed: int
    failures: list[dict[str, Any]]
    by_type: dict[str, dict[str, int]]

    @property
    def top1_rate(self) -> float:
        return self.top1_hits / self.total if self.total else 0.0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def evaluate_resource_questions(
    package: KnowledgePackage,
    limit: int | None = None,
    use_vectors: bool = False,
    use_db: bool = False,
    database_url: str | None = None,
) -> ResourceEvalResult:
    state = ApiState(package, database_url=database_url)
    cases = package.resource_eval_cases[:limit] if limit else package.resource_eval_cases
    failures: list[dict[str, Any]] = []
    top1_hits = 0
    passed = 0
    by_type: dict[str, dict[str, int]] = {}

    for case in cases:
        question = str(case.get("question") or "")
        expected = str(case.get("expected_resource_id") or "")
        expected_type = str(case.get("expected_resource_type") or "")
        by_type.setdefault(expected_type, {"total": 0, "passed": 0})
        by_type[expected_type]["total"] += 1

        payload = answer_payload(
            state,
            question,
            top_k=5,
            use_vectors=use_vectors,
            use_db=use_db,
        )
        actual_answer_id = str(payload.get("answer_id") or "")
        actual_resource_id = actual_answer_id[len("resource:") :] if actual_answer_id.startswith("resource:") else ""
        recommended_ids = [
            str(item.get("resource_id") or "")
            for item in payload.get("recommended_resources", [])
            if isinstance(item, dict)
        ]

        if actual_resource_id == expected:
            top1_hits += 1

        case_passed = (
            actual_resource_id == expected
            and payload.get("answer_mode") == "resource_guidance"
            and expected in recommended_ids[:3]
        )
        if case_passed:
            passed += 1
            by_type[expected_type]["passed"] += 1
        else:
            failures.append(
                {
                    "test_id": case.get("test_id"),
                    "question": question,
                    "expected_resource_id": expected,
                    "actual_answer_id": actual_answer_id,
                    "actual_resource_id": actual_resource_id,
                    "answer_mode": payload.get("answer_mode"),
                    "recommended_resource_ids": recommended_ids,
                    "trace": payload.get("trace"),
                }
            )

    return ResourceEvalResult(
        total=len(cases),
        top1_hits=top1_hits,
        passed=passed,
        failures=failures,
        by_type=by_type,
    )


def write_resource_eval_report(
    result: ResourceEvalResult,
    report_path: str | Path,
    failures_path: str | Path,
    chapter_label: str = "知识库",
) -> None:
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {chapter_label}资源导向问答评测报告",
        "",
        f"- 测试问题总数：{result.total}",
        f"- Top1 资源命中率：{result.top1_hits}/{result.total} = {result.top1_rate:.2%}",
        f"- 通过率：{result.passed}/{result.total} = {result.pass_rate:.2%}",
        f"- 失败样例数：{len(result.failures)}",
        "",
        "## 按资源类型统计",
        "",
        "| 资源类型 | 通过 | 总数 | 通过率 |",
        "|---|---:|---:|---:|",
    ]
    for resource_type, stats in sorted(result.by_type.items()):
        total = stats["total"]
        ok = stats["passed"]
        lines.append(f"| {resource_type or '未标注'} | {ok} | {total} | {(ok / total if total else 0):.2%} |")

    lines.extend(["", "## 失败样例 Top 20", ""])
    if not result.failures:
        lines.append("无失败样例。")
    for failure in result.failures[:20]:
        lines.append(
            f"- `{failure['test_id']}` 期望 `{failure['expected_resource_id']}`，"
            f"实际 `{failure['actual_answer_id']}`：{failure['question']}"
        )

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(failures_path, result.failures)
