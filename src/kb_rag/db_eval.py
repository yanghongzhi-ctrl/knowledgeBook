from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg

from .db_retrieve import DEFAULT_DATABASE_URL, DEFAULT_VERSION_ID, DbHybridAnswerRetriever, database_url
from .evaluate import _format_ok
from .loader import KnowledgePackage
from .render import render_answer
from .retrieve import AnswerRetriever, RetrievalHit, confidence, coverage


@dataclass(frozen=True)
class DbEvalResult:
    run_id: str
    total: int
    top1_hits: int
    top3_hits: int
    passed: int
    retriever: str

    @property
    def top1_rate(self) -> float:
        return self.top1_hits / self.total if self.total else 0.0

    @property
    def top3_rate(self) -> float:
        return self.top3_hits / self.total if self.total else 0.0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def metrics(self) -> dict[str, Any]:
        return {
            "retriever": self.retriever,
            "total": self.total,
            "top1_hits": self.top1_hits,
            "top1_rate": round(self.top1_rate, 6),
            "top3_hits": self.top3_hits,
            "top3_rate": round(self.top3_rate, 6),
            "passed": self.passed,
            "pass_rate": round(self.pass_rate, 6),
        }


def run_db_evaluation(
    package: KnowledgePackage,
    dsn: str | None = None,
    version_id: str = DEFAULT_VERSION_ID,
    retriever_mode: str = "keyword",
    limit: int | None = None,
    top_k: int = 5,
    report_path: str | Path | None = None,
) -> DbEvalResult:
    dsn = dsn or database_url(DEFAULT_DATABASE_URL)
    run_id = _run_id(retriever_mode, package)
    cases = package.qa_cases[:limit] if limit else package.qa_cases
    retriever = _make_retriever(package, retriever_mode, dsn=dsn, version_id=version_id)
    _start_run(dsn=dsn, version_id=version_id, run_id=run_id, retriever_mode=retriever_mode, report_path=report_path)

    top1_hits = 0
    top3_hits = 0
    passed = 0
    rows: list[dict[str, Any]] = []

    for case in cases:
        question = str(case.get("question", ""))
        expected = str(case.get("expected_answer_card", ""))
        mode = str(case.get("required_response_mode", ""))
        hits, extra_trace = _search(retriever, retriever_mode, question, top_k=top_k)
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
        missing_points = _missing_points(expected_points, answer)
        unexpected = [item for item in should_not_include if str(item) and str(item) in answer]
        format_ok = _format_ok(mode, answer)
        case_passed = actual == expected and point_coverage >= 0.7 and not unexpected and format_ok
        if case_passed:
            passed += 1

        score = hits[0].score if hits else 0.0
        rows.append(
            {
                "test_id": case.get("test_id"),
                "expected_answer_card": expected,
                "actual_answer_card": actual,
                "passed": case_passed,
                "score": score,
                "missing_points": missing_points,
                "unexpected_content": unexpected,
                "trace": {
                    "question": question,
                    "retriever": retriever_mode,
                    "top_hits": [_hit_to_trace(hit) for hit in hits],
                    "confidence": confidence(score) if hits else "none",
                    "point_coverage": round(point_coverage, 6),
                    "format_ok": format_ok,
                    "extra": extra_trace,
                },
            }
        )

    result = DbEvalResult(
        run_id=run_id,
        total=len(cases),
        top1_hits=top1_hits,
        top3_hits=top3_hits,
        passed=passed,
        retriever=retriever_mode,
    )
    _write_cases_and_finish(
        dsn=dsn,
        run_id=run_id,
        rows=rows,
        metrics=result.metrics(),
    )
    return result


def latest_eval_runs(dsn: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    dsn = dsn or database_url(DEFAULT_DATABASE_URL)
    sql = """
        SELECT run_id, version_id, started_at, finished_at, metrics, report_path
        FROM rag_eval_runs
        ORDER BY started_at DESC
        LIMIT %s
    """
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [
        {
            "run_id": row[0],
            "version_id": row[1],
            "started_at": row[2].isoformat() if row[2] else None,
            "finished_at": row[3].isoformat() if row[3] else None,
            "metrics": row[4],
            "report_path": row[5],
        }
        for row in rows
    ]


def eval_failures(dsn: str | None = None, run_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    dsn = dsn or database_url(DEFAULT_DATABASE_URL)
    if not run_id:
        run_id_sql = "SELECT run_id FROM rag_eval_runs ORDER BY started_at DESC LIMIT 1"
        with psycopg.connect(dsn) as conn:
            latest = conn.execute(run_id_sql).fetchone()
        if not latest:
            return []
        run_id = latest[0]

    sql = """
        SELECT
          c.test_id,
          q.question,
          c.expected_answer_card,
          c.actual_answer_card,
          c.score,
          c.missing_points,
          c.unexpected_content,
          c.trace
        FROM rag_eval_cases c
        JOIN qa_evaluation_testset q
          ON q.test_id = c.test_id
        WHERE c.run_id = %s
          AND c.passed IS NOT TRUE
        ORDER BY c.test_id
        LIMIT %s
    """
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, (run_id, limit)).fetchall()
    return [
        {
            "run_id": run_id,
            "test_id": row[0],
            "question": row[1],
            "expected_answer_card": row[2],
            "actual_answer_card": row[3],
            "score": float(row[4]) if row[4] is not None else None,
            "missing_points": row[5],
            "unexpected_content": row[6],
            "trace": row[7],
        }
        for row in rows
    ]


def _make_retriever(package: KnowledgePackage, mode: str, dsn: str, version_id: str) -> Any:
    if mode == "keyword":
        return AnswerRetriever(package)
    if mode == "db-hybrid":
        return DbHybridAnswerRetriever(package, dsn=dsn, version_id=version_id)
    raise ValueError(f"Unsupported retriever mode: {mode}")


def _search(retriever: Any, mode: str, question: str, top_k: int) -> tuple[list[RetrievalHit], dict[str, Any] | None]:
    if mode == "db-hybrid":
        hits, trace = retriever.search_with_trace(question, top_k=top_k)
        return hits, {
            "keyword_top": trace.keyword_top,
            "vector_top": trace.vector_top,
            "hybrid_top": trace.hybrid_top,
        }
    return retriever.search(question, top_k=top_k), None


def _start_run(
    dsn: str,
    version_id: str,
    run_id: str,
    retriever_mode: str,
    report_path: str | Path | None,
) -> None:
    metrics = {"retriever": retriever_mode, "status": "running"}
    sql = """
        INSERT INTO rag_eval_runs (run_id, version_id, metrics, report_path)
        VALUES (%s, %s, %s::jsonb, %s)
    """
    with psycopg.connect(dsn) as conn:
        conn.execute(
            sql,
            (
                run_id,
                version_id,
                json.dumps(metrics, ensure_ascii=False),
                str(report_path) if report_path else None,
            ),
        )


def _write_cases_and_finish(
    dsn: str,
    run_id: str,
    rows: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> None:
    case_sql = """
        INSERT INTO rag_eval_cases (
          run_id, test_id, expected_answer_card, actual_answer_card, passed,
          score, missing_points, unexpected_content, trace
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
    """
    finish_sql = "UPDATE rag_eval_runs SET finished_at = now(), metrics = %s::jsonb WHERE run_id = %s"
    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            for row in rows:
                conn.execute(
                    case_sql,
                    (
                        run_id,
                        row["test_id"],
                        row["expected_answer_card"],
                        row["actual_answer_card"],
                        row["passed"],
                        row["score"],
                        json.dumps(row["missing_points"], ensure_ascii=False),
                        json.dumps(row["unexpected_content"], ensure_ascii=False),
                        json.dumps(row["trace"], ensure_ascii=False),
                    ),
                )
            conn.execute(finish_sql, (json.dumps(metrics, ensure_ascii=False), run_id))


def _hit_to_trace(hit: RetrievalHit) -> dict[str, Any]:
    return {
        "answer_id": hit.answer_id,
        "score": round(hit.score, 6),
        "confidence": confidence(hit.score),
        "reasons": hit.reasons,
        "canonical_question": hit.card.get("canonical_question"),
        "answer_mode": hit.card.get("answer_mode"),
    }


def _missing_points(expected_points: list[Any], answer: str) -> list[str]:
    answer_text = answer or ""
    return [str(point) for point in expected_points if str(point) and str(point) not in answer_text]


def _run_id(retriever_mode: str, package: KnowledgePackage) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"eval_{_chapter_id(package)}_{retriever_mode.replace('-', '_')}_{stamp}"


def _chapter_id(package: KnowledgePackage) -> str:
    for rows in (package.answer_cards, package.knowledge_points, package.resources):
        for row in rows:
            if isinstance(row, dict) and row.get("chapter_id"):
                return str(row["chapter_id"])
    return "ch01"
