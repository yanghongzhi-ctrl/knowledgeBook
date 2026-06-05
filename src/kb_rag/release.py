from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg

from .db_eval import run_db_evaluation
from .embeddings import (
    DEFAULT_MODEL,
    build_embedding_records,
    summarize_records,
    write_embedding_jsonl,
    write_embedding_update_sql,
)
from .evaluate import evaluate_package, write_eval_report
from .export import export_processed
from .loader import KnowledgePackage, table_counts, write_json
from .quality import write_quality_report
from .resource_eval import evaluate_resource_questions, write_resource_eval_report
from .sql_export import write_seed_sql
from .validate import validate_package


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/road_kb"


@dataclass
class ReleaseStep:
    name: str
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReleaseResult:
    chapter_id: str
    version_id: str
    package_path: str
    started_at: str
    finished_at: str
    status: str
    steps: list[ReleaseStep]
    report_path: str
    json_path: str


def run_release(
    package: KnowledgePackage,
    *,
    processed_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    database_url: str = DEFAULT_DATABASE_URL,
    model: str = DEFAULT_MODEL,
    base_url: str = "http://127.0.0.1:11434",
    batch_size: int = 8,
    generate_embeddings: bool = False,
    apply_db: bool = False,
    apply_migration: bool = False,
    db_hybrid_limit: int = 30,
    min_pass_rate: float = 1.0,
) -> ReleaseResult:
    started = datetime.now()
    chapter_id = infer_chapter_id(package)
    chapter_label = infer_chapter_label(package)
    version_id = f"{chapter_id}_kb_v1.0"
    processed = Path(processed_dir) if processed_dir else PROJECT_ROOT / "data" / "processed" / chapter_id
    output = Path(output_dir) if output_dir else PROJECT_ROOT / "output" / f"{chapter_id}_rag_engine"
    reports = output / "reports"
    db_load = output / "db_load"
    embeddings_dir = output / "embeddings"
    reports.mkdir(parents=True, exist_ok=True)
    db_load.mkdir(parents=True, exist_ok=True)
    embeddings_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports / f"release_report_{chapter_id}.md"
    json_path = reports / f"release_report_{chapter_id}.json"
    steps: list[ReleaseStep] = []
    blocking_failure = False

    validation = validate_package(package)
    steps.append(
        ReleaseStep(
            "validate",
            "passed" if validation.ok else "failed",
            f"errors={len(validation.errors)}, warnings={len(validation.warnings)}",
            {
                "counts": validation.counts,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        )
    )
    if not validation.ok:
        blocking_failure = True

    if not blocking_failure:
        quality_path = reports / f"kb_quality_report_{chapter_id}.json"
        write_quality_report(package, quality_path)
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        steps.append(
            ReleaseStep(
                "quality",
                "passed",
                (
                    f"ambiguous_qa={len(quality.get('ambiguous_qa_cases', []))}, "
                    f"duplicate_canonical={len(quality.get('duplicate_canonical_questions', []))}"
                ),
                {"report": str(quality_path), **quality},
            )
        )

        exported = export_processed(package, processed)
        steps.append(
            ReleaseStep(
                "export",
                "passed",
                f"exported_files={len(exported)}",
                {"output_dir": str(processed), "counts": exported},
            )
        )

        seed_path = db_load / f"{chapter_id}_seed.sql"
        write_seed_sql(package, seed_path, status="draft")
        steps.append(
            ReleaseStep(
                "sql_export",
                "passed",
                f"seed_sql_bytes={seed_path.stat().st_size}",
                {"seed_sql": str(seed_path)},
            )
        )

        qa_report = reports / f"eval_report_{chapter_id}.md"
        qa_failures = reports / f"failed_cases_{chapter_id}.json"
        qa_result = evaluate_package(package)
        write_eval_report(qa_result, qa_report, qa_failures)
        qa_ok = qa_result.pass_rate >= min_pass_rate
        steps.append(
            ReleaseStep(
                "local_qa_evaluation",
                "passed" if qa_ok else "failed",
                f"passed={qa_result.passed}/{qa_result.total} ({qa_result.pass_rate:.2%})",
                {
                    "total": qa_result.total,
                    "top1_hits": qa_result.top1_hits,
                    "top3_hits": qa_result.top3_hits,
                    "passed": qa_result.passed,
                    "pass_rate": qa_result.pass_rate,
                    "report": str(qa_report),
                    "failures": str(qa_failures),
                },
            )
        )
        if not qa_ok:
            blocking_failure = True

        resource_report = reports / f"resource_eval_report_{chapter_id}.md"
        resource_failures = reports / f"resource_failed_cases_{chapter_id}.json"
        resource_result = evaluate_resource_questions(package)
        write_resource_eval_report(resource_result, resource_report, resource_failures, chapter_label=chapter_label)
        resource_ok = resource_result.pass_rate >= min_pass_rate
        steps.append(
            ReleaseStep(
                "local_resource_evaluation",
                "passed" if resource_ok else "failed",
                f"passed={resource_result.passed}/{resource_result.total} ({resource_result.pass_rate:.2%})",
                {
                    "total": resource_result.total,
                    "top1_hits": resource_result.top1_hits,
                    "passed": resource_result.passed,
                    "pass_rate": resource_result.pass_rate,
                    "report": str(resource_report),
                    "failures": str(resource_failures),
                },
            )
        )
        if not resource_ok:
            blocking_failure = True

        vector_jsonl = embeddings_dir / f"{chapter_id}_embedding_vectors.jsonl"
        embedding_sql = db_load / f"{chapter_id}_embedding_updates.sql"
        if generate_embeddings and not blocking_failure:
            try:
                records = build_embedding_records(
                    package,
                    model=model,
                    base_url=base_url,
                    batch_size=batch_size,
                )
                write_embedding_jsonl(records, vector_jsonl)
                write_embedding_update_sql(records, embedding_sql)
                summary = summarize_records(records)
                expected = len(package.data.get("Embedding_Corpus", []))
                embeddings_ok = len(records) == expected and summary.get("dimensions") == [1024]
                steps.append(
                    ReleaseStep(
                        "embeddings",
                        "passed" if embeddings_ok else "failed",
                        f"generated={len(records)}/{expected}, dimensions={summary.get('dimensions')}",
                        {
                            "jsonl": str(vector_jsonl),
                            "sql": str(embedding_sql),
                            **summary,
                        },
                    )
                )
                if not embeddings_ok:
                    blocking_failure = True
            except Exception as exc:
                steps.append(ReleaseStep("embeddings", "failed", str(exc)))
                blocking_failure = True
        else:
            steps.append(
                ReleaseStep(
                    "embeddings",
                    "skipped",
                    "embedding generation not requested" if not generate_embeddings else "blocked by earlier failure",
                    {
                        "existing_jsonl": str(vector_jsonl) if vector_jsonl.exists() else None,
                        "existing_sql": str(embedding_sql) if embedding_sql.exists() else None,
                    },
                )
            )

        if apply_db and not blocking_failure:
            try:
                if apply_migration:
                    migration = PROJECT_ROOT / "src" / "db" / "migrations" / "001_init_pgvector.sql"
                    _run_psql(database_url, migration)
                    steps.append(ReleaseStep("db_migration", "passed", str(migration)))

                _run_psql(database_url, seed_path)
                if embedding_sql.exists():
                    _run_psql(database_url, embedding_sql)
                else:
                    raise RuntimeError(f"Embedding update SQL does not exist: {embedding_sql}")

                db_counts = _database_counts(database_url, version_id)
                expected_counts = _expected_database_counts(package)
                count_mismatches = {
                    key: {"expected": expected, "actual": db_counts.get(key, 0)}
                    for key, expected in expected_counts.items()
                    if db_counts.get(key, 0) != expected
                }
                db_ok = not count_mismatches and db_counts.get("embedded_vectors", 0) == expected_counts["embedding_corpus"]
                steps.append(
                    ReleaseStep(
                        "db_import",
                        "passed" if db_ok else "failed",
                        f"counts_ok={not count_mismatches}, embedded_vectors={db_counts.get('embedded_vectors', 0)}",
                        {
                            "version_id": version_id,
                            "counts": db_counts,
                            "expected_counts": expected_counts,
                            "mismatches": count_mismatches,
                        },
                    )
                )
                if not db_ok:
                    blocking_failure = True
            except Exception as exc:
                steps.append(ReleaseStep("db_import", "failed", str(exc)))
                blocking_failure = True
        else:
            steps.append(
                ReleaseStep(
                    "db_import",
                    "skipped",
                    "database import not requested" if not apply_db else "blocked by earlier failure",
                )
            )

        if apply_db and not blocking_failure:
            keyword_report = reports / f"eval_report_{chapter_id}_db_keyword.md"
            keyword_result = run_db_evaluation(
                package,
                dsn=database_url,
                version_id=version_id,
                retriever_mode="keyword",
                report_path=keyword_report,
            )
            keyword_ok = keyword_result.pass_rate >= min_pass_rate
            steps.append(
                ReleaseStep(
                    "db_keyword_evaluation",
                    "passed" if keyword_ok else "failed",
                    f"passed={keyword_result.passed}/{keyword_result.total} ({keyword_result.pass_rate:.2%})",
                    keyword_result.metrics(),
                )
            )
            if not keyword_ok:
                blocking_failure = True

        if apply_db and not blocking_failure and db_hybrid_limit > 0:
            hybrid_report = reports / f"eval_report_{chapter_id}_db_hybrid.md"
            try:
                hybrid_result = run_db_evaluation(
                    package,
                    dsn=database_url,
                    version_id=version_id,
                    retriever_mode="db-hybrid",
                    limit=db_hybrid_limit,
                    report_path=hybrid_report,
                )
                hybrid_ok = hybrid_result.pass_rate >= min_pass_rate
                steps.append(
                    ReleaseStep(
                        "db_hybrid_evaluation",
                        "passed" if hybrid_ok else "failed",
                        f"passed={hybrid_result.passed}/{hybrid_result.total} ({hybrid_result.pass_rate:.2%})",
                        hybrid_result.metrics(),
                    )
                )
                if not hybrid_ok:
                    blocking_failure = True
            except Exception as exc:
                steps.append(ReleaseStep("db_hybrid_evaluation", "failed", str(exc)))
                blocking_failure = True

        if apply_db and not blocking_failure:
            _mark_released(database_url, version_id)
            steps.append(ReleaseStep("mark_released", "passed", f"version_id={version_id}"))
    else:
        steps.append(ReleaseStep("release_pipeline", "skipped", "blocked by validation errors"))

    finished = datetime.now()
    status = "released" if apply_db and not blocking_failure else ("ready" if not blocking_failure else "failed")
    result = ReleaseResult(
        chapter_id=chapter_id,
        version_id=version_id,
        package_path=str(package.path),
        started_at=started.isoformat(timespec="seconds"),
        finished_at=finished.isoformat(timespec="seconds"),
        status=status,
        steps=steps,
        report_path=str(report_path),
        json_path=str(json_path),
    )
    _write_release_reports(result, package, report_path, json_path)
    return result


def infer_chapter_id(package: KnowledgePackage) -> str:
    for rows in (package.answer_cards, package.knowledge_points, package.resources):
        for row in rows:
            if isinstance(row, dict) and row.get("chapter_id"):
                return str(row["chapter_id"])
    return "ch01"


def infer_chapter_label(package: KnowledgePackage) -> str:
    rows = package.data.get("Chapter_Structure", [])
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and str(row.get("level", "")).lower() in {"chapter", "章"}:
                return str(row.get("title") or infer_chapter_id(package))
    return infer_chapter_id(package)


def _run_psql(database_url: str, sql_path: Path) -> None:
    psql = _find_psql()
    completed = subprocess.run(
        [str(psql), "-d", database_url, "-v", "ON_ERROR_STOP=1", "-f", str(sql_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"psql failed for {sql_path.name}: {message[-2000:]}")


def _find_psql() -> Path:
    found = shutil.which("psql")
    if found:
        return Path(found)
    bundled = PROJECT_ROOT / ".mamba" / "pgvector" / "Library" / "bin" / "psql.exe"
    if bundled.exists():
        return bundled
    raise RuntimeError("psql was not found in PATH or the project .mamba runtime")


def _expected_database_counts(package: KnowledgePackage) -> dict[str, int]:
    return {
        "answer_cards": len(package.answer_cards),
        "knowledge_points": len(package.knowledge_points),
        "source_chunks": len(package.source_chunks),
        "qa_evaluation_testset": len(package.qa_cases),
        "resources": len(package.resources),
        "interactive_scripts": len(package.interactive_scripts),
        "resource_evaluation_testset": len(package.resource_eval_cases),
        "embedding_corpus": len(package.data.get("Embedding_Corpus", [])),
    }


def _database_counts(database_url: str, version_id: str) -> dict[str, int]:
    tables = [
        "answer_cards",
        "knowledge_points",
        "source_chunks",
        "qa_evaluation_testset",
        "resources",
        "interactive_scripts",
        "resource_evaluation_testset",
        "embedding_corpus",
    ]
    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as conn:
        for table in tables:
            row = conn.execute(f"SELECT count(*) FROM {table} WHERE version_id = %s", (version_id,)).fetchone()
            counts[table] = int(row[0])
        row = conn.execute(
            "SELECT count(*) FROM embedding_corpus WHERE version_id = %s AND embedding IS NOT NULL",
            (version_id,),
        ).fetchone()
        counts["embedded_vectors"] = int(row[0])
    return counts


def _mark_released(database_url: str, version_id: str) -> None:
    with psycopg.connect(database_url) as conn:
        updated = conn.execute(
            "UPDATE kb_versions SET status = 'released' WHERE version_id = %s",
            (version_id,),
        ).rowcount
        if updated != 1:
            raise RuntimeError(f"Unable to mark version as released: {version_id}")


def _write_release_reports(
    result: ReleaseResult,
    package: KnowledgePackage,
    report_path: Path,
    json_path: Path,
) -> None:
    payload = {
        "chapter_id": result.chapter_id,
        "version_id": result.version_id,
        "package_path": result.package_path,
        "source_checksum": hashlib.sha256(package.path.read_bytes()).hexdigest(),
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "status": result.status,
        "table_counts": table_counts(package),
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "summary": step.summary,
                "details": step.details,
            }
            for step in result.steps
        ],
    }
    write_json(json_path, payload)

    lines = [
        f"# {result.chapter_id} 知识库发布报告",
        "",
        f"- 版本：`{result.version_id}`",
        f"- 状态：`{result.status}`",
        f"- 知识包：`{result.package_path}`",
        f"- 开始时间：{result.started_at}",
        f"- 完成时间：{result.finished_at}",
        "",
        "## 发布步骤",
        "",
        "| 步骤 | 状态 | 摘要 |",
        "|---|---|---|",
    ]
    for step in result.steps:
        lines.append(f"| {step.name} | {step.status} | {_md_escape(step.summary)} |")

    validation = next((step for step in result.steps if step.name == "validate"), None)
    if validation:
        errors = validation.details.get("errors", [])
        warnings = validation.details.get("warnings", [])
        lines.extend(["", "## 校验问题", ""])
        if not errors and not warnings:
            lines.append("无错误或警告。")
        for error in errors:
            lines.append(f"- 错误：{error}")
        for warning in warnings[:100]:
            lines.append(f"- 警告：{warning}")
        if len(warnings) > 100:
            lines.append(f"- 其余警告：{len(warnings) - 100} 条，详见 JSON 报告。")

    lines.extend(
        [
            "",
            "## 结论",
            "",
            (
                "本版本已通过发布门槛并标记为 released。"
                if result.status == "released"
                else "本版本已通过本地发布检查，可在数据库服务与嵌入服务就绪后执行完整发布。"
                if result.status == "ready"
                else "本版本未通过发布门槛，请修复失败步骤后重新发布。"
            ),
            "",
            f"JSON 详情：`{json_path}`",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _md_escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")
