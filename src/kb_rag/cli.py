from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .evaluate import evaluate_package, write_eval_report
from .export import export_processed
from .embeddings import (
    DEFAULT_MODEL,
    build_embedding_records,
    summarize_records,
    write_embedding_jsonl,
    write_embedding_update_sql,
    vector_search,
)
from .db_retrieve import DEFAULT_DATABASE_URL, DEFAULT_VERSION_ID, DbHybridAnswerRetriever, PgVectorSearcher
from .db_eval import latest_eval_runs, run_db_evaluation
from .hybrid import DEFAULT_VECTOR_PATH, HybridAnswerRetriever, write_hybrid_report
from .loader import load_package, table_counts
from .quality import write_quality_report
from .render import render_answer
from .release import infer_chapter_label, run_release
from .resource_eval import evaluate_resource_questions, write_resource_eval_report
from .resources import build_bound_resources, recommend_resources
from .retrieve import AnswerRetriever
from .sql_export import write_seed_sql
from .trace import write_trace_samples
from .validate import validate_package


DEFAULT_PACKAGE = Path("data/raw/ch01/第1章_道路工程数字化设计概述_知识库_v1.0完备版.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kb-rag", description="Road engineering KB RAG toolkit")
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE), help="Knowledge package JSON path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary", help="Print package table counts")
    sub.add_parser("validate", help="Validate package schema")

    export_parser = sub.add_parser("export", help="Export processed table JSON files")
    export_parser.add_argument("--out", default="data/processed/ch01")

    sql_parser = sub.add_parser("sql-export", help="Generate PostgreSQL seed SQL")
    sql_parser.add_argument("--out", default="output/ch01_rag_engine/db_load/ch01_seed.sql")

    resources_parser = sub.add_parser("bind-resources", help="Bind chapter 1 HTML resources")
    resources_parser.add_argument("--out", default="data/processed/ch01/resource_bindings.json")

    trace_parser = sub.add_parser("trace", help="Generate RAG trace samples")
    trace_parser.add_argument("--out", default="output/ch01_rag_engine/reports/rag_trace_samples_ch01.json")

    quality_parser = sub.add_parser("quality", help="Generate KB quality report")
    quality_parser.add_argument("--out", default="output/ch01_rag_engine/reports/kb_quality_report_ch01.json")

    embed_parser = sub.add_parser("embed", help="Generate embeddings using local Ollama")
    embed_parser.add_argument("--model", default=DEFAULT_MODEL)
    embed_parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    embed_parser.add_argument("--batch-size", type=int, default=8)
    embed_parser.add_argument("--limit", type=int, default=0)
    embed_parser.add_argument("--jsonl", default="output/ch01_rag_engine/embeddings/ch01_embedding_vectors.jsonl")
    embed_parser.add_argument("--sql", default="output/ch01_rag_engine/db_load/ch01_embedding_updates.sql")

    vector_parser = sub.add_parser("vector-search", help="Search cached embeddings")
    vector_parser.add_argument("question")
    vector_parser.add_argument("--model", default=DEFAULT_MODEL)
    vector_parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    vector_parser.add_argument("--vectors", default="output/ch01_rag_engine/embeddings/ch01_embedding_vectors.jsonl")
    vector_parser.add_argument("--source-type", default="answer_card")
    vector_parser.add_argument("--top-k", type=int, default=5)

    hybrid_parser = sub.add_parser("hybrid-ask", help="Run keyword + cached vector retrieval")
    hybrid_parser.add_argument("question")
    hybrid_parser.add_argument("--model", default=DEFAULT_MODEL)
    hybrid_parser.add_argument("--vectors", default=str(DEFAULT_VECTOR_PATH))
    hybrid_parser.add_argument("--top-k", type=int, default=5)

    db_vector_parser = sub.add_parser("db-vector-search", help="Search PostgreSQL/pgvector embeddings")
    db_vector_parser.add_argument("question")
    db_vector_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    db_vector_parser.add_argument("--version-id", default=DEFAULT_VERSION_ID)
    db_vector_parser.add_argument("--model", default=DEFAULT_MODEL)
    db_vector_parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    db_vector_parser.add_argument("--top-k", type=int, default=5)

    db_hybrid_parser = sub.add_parser("db-hybrid-ask", help="Run keyword + PostgreSQL/pgvector retrieval")
    db_hybrid_parser.add_argument("question")
    db_hybrid_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    db_hybrid_parser.add_argument("--version-id", default=DEFAULT_VERSION_ID)
    db_hybrid_parser.add_argument("--model", default=DEFAULT_MODEL)
    db_hybrid_parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    db_hybrid_parser.add_argument("--top-k", type=int, default=5)

    sub.add_parser("db-summary", help="Print PostgreSQL table counts")

    db_eval_parser = sub.add_parser("db-evaluate", help="Run QA evaluation and persist results to PostgreSQL")
    db_eval_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    db_eval_parser.add_argument("--version-id", default=DEFAULT_VERSION_ID)
    db_eval_parser.add_argument("--retriever", choices=["keyword", "db-hybrid"], default="keyword")
    db_eval_parser.add_argument("--limit", type=int, default=0)
    db_eval_parser.add_argument("--top-k", type=int, default=5)
    db_eval_parser.add_argument("--report", default="output/ch01_rag_engine/reports/eval_report_ch01.md")

    db_runs_parser = sub.add_parser("db-eval-runs", help="List recent persisted QA evaluation runs")
    db_runs_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    db_runs_parser.add_argument("--limit", type=int, default=5)

    hybrid_report_parser = sub.add_parser("hybrid-report", help="Generate hybrid retrieval comparison report")
    hybrid_report_parser.add_argument("--model", default=DEFAULT_MODEL)
    hybrid_report_parser.add_argument("--vectors", default=str(DEFAULT_VECTOR_PATH))
    hybrid_report_parser.add_argument("--out", default="output/ch01_rag_engine/reports/hybrid_retrieval_report_ch01.json")

    ask_parser = sub.add_parser("ask", help="Run a retrieval + render sample")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--top-k", type=int, default=5)

    eval_parser = sub.add_parser("evaluate", help="Run QA_Evaluation_Testset")
    eval_parser.add_argument("--limit", type=int, default=0)
    eval_parser.add_argument("--report", default="output/ch01_rag_engine/reports/eval_report_ch01.md")
    eval_parser.add_argument("--failures", default="output/ch01_rag_engine/reports/failed_cases_ch01.json")

    resource_eval_parser = sub.add_parser("resource-evaluate", help="Run Resource_Evaluation_Testset")
    resource_eval_parser.add_argument("--limit", type=int, default=0)
    resource_eval_parser.add_argument("--use-vectors", action="store_true")
    resource_eval_parser.add_argument("--use-db", action="store_true")
    resource_eval_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    resource_eval_parser.add_argument("--report", default="output/ch01_rag_engine/reports/resource_eval_report_ch01.md")
    resource_eval_parser.add_argument("--failures", default="output/ch01_rag_engine/reports/resource_failed_cases_ch01.json")

    release_parser = sub.add_parser("release", help="Run validation, export, evaluation, and optional full database release")
    release_parser.add_argument("--processed-dir")
    release_parser.add_argument("--output-dir")
    release_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    release_parser.add_argument("--model", default=DEFAULT_MODEL)
    release_parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    release_parser.add_argument("--batch-size", type=int, default=8)
    release_parser.add_argument("--generate-embeddings", action="store_true")
    release_parser.add_argument("--apply-db", action="store_true")
    release_parser.add_argument("--apply-migration", action="store_true")
    release_parser.add_argument("--db-hybrid-limit", type=int, default=30)
    release_parser.add_argument("--min-pass-rate", type=float, default=1.0)

    args = parser.parse_args(argv)
    package = load_package(args.package)

    if args.command == "summary":
        for table, count in sorted(table_counts(package).items()):
            print(f"{table}: {count}")
        return 0

    if args.command == "validate":
        report = validate_package(package)
        print("Validation:", "OK" if report.ok else "FAILED")
        print("Tables:")
        for table, count in sorted(report.counts.items()):
            print(f"  {table}: {count}")
        if report.errors:
            print("\nErrors:")
            for error in report.errors:
                print(f"  - {error}")
        if report.warnings:
            print("\nWarnings:")
            for warning in report.warnings[:50]:
                print(f"  - {warning}")
            if len(report.warnings) > 50:
                print(f"  ... {len(report.warnings) - 50} more warnings")
        return 0 if report.ok else 1

    if args.command == "export":
        counts = export_processed(package, args.out)
        for filename, count in sorted(counts.items()):
            print(f"{filename}: {count}")
        return 0

    if args.command == "sql-export":
        output = write_seed_sql(package, args.out)
        print(f"seed_sql={output}")
        return 0

    if args.command == "bind-resources":
        from .loader import write_json

        resources = build_bound_resources(package.resources)
        write_json(args.out, resources)
        bound = sum(1 for item in resources if item.get("status") == "bound")
        print(f"resources={len(resources)}")
        print(f"bound={bound}")
        print(f"out={args.out}")
        return 0

    if args.command == "trace":
        output = write_trace_samples(package, args.out)
        print(f"trace={output}")
        return 0

    if args.command == "quality":
        output = write_quality_report(package, args.out)
        print(f"quality={output}")
        return 0

    if args.command == "embed":
        records = build_embedding_records(
            package,
            model=args.model,
            base_url=args.base_url,
            batch_size=args.batch_size,
            limit=args.limit if args.limit and args.limit > 0 else None,
        )
        jsonl_path = write_embedding_jsonl(records, args.jsonl)
        sql_path = write_embedding_update_sql(records, args.sql)
        summary = summarize_records(records)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"jsonl={jsonl_path}")
        print(f"sql={sql_path}")
        return 0

    if args.command == "vector-search":
        results = vector_search(
            args.question,
            vector_path=args.vectors,
            model=args.model,
            base_url=args.base_url,
            source_type=args.source_type,
            top_k=args.top_k,
        )
        for idx, result in enumerate(results, 1):
            print(
                f"{idx}. {result['source_id']} sim={result['similarity']:.4f} "
                f"dim={result['dimensions']} model={result['model']}"
            )
        return 0

    if args.command == "hybrid-ask":
        retriever = HybridAnswerRetriever(package, vector_path=args.vectors, model=args.model)
        hits, trace = retriever.search_with_trace(args.question, top_k=args.top_k)
        if not hits:
            print("教材知识库未找到直接答案。")
            return 2
        print("Keyword top:")
        for item in trace.keyword_top:
            print(f"- {item['answer_id']} score={item['score']} {item['canonical_question']}")
        print("\nVector top:")
        for item in trace.vector_top:
            print(f"- {item['source_id']} sim={item['similarity']:.4f}")
        print("\nHybrid top:")
        for hit in hits:
            print(f"- {hit.answer_id} score={hit.score:.2f} reasons={','.join(hit.reasons)}")
        print("\nAnswer:\n")
        print(render_answer(hits[0].card))
        return 0

    if args.command == "db-vector-search":
        searcher = PgVectorSearcher(
            dsn=args.database_url,
            version_id=args.version_id,
            model=args.model,
            base_url=args.base_url,
        )
        for idx, hit in enumerate(searcher.search_answer_cards(args.question, top_k=args.top_k), 1):
            print(f"{idx}. {hit.source_id} sim={hit.similarity:.4f} embedding={hit.embedding_id}")
        return 0

    if args.command == "db-hybrid-ask":
        retriever = DbHybridAnswerRetriever(
            package,
            dsn=args.database_url,
            version_id=args.version_id,
            model=args.model,
            base_url=args.base_url,
        )
        hits, trace = retriever.search_with_trace(args.question, top_k=args.top_k)
        if not hits:
            print("No direct answer found in the knowledge base.")
            return 2
        print("DB vector top:")
        for item in trace.vector_top:
            print(f"- {item['source_id']} sim={item['similarity']:.4f}")
        print("\nHybrid top:")
        for hit in hits:
            print(f"- {hit.answer_id} score={hit.score:.2f} reasons={','.join(hit.reasons)}")
        print("\nAnswer:\n")
        print(render_answer(hits[0].card))
        return 0

    if args.command == "db-summary":
        searcher = PgVectorSearcher()
        for table, count in sorted(searcher.table_counts().items()):
            print(f"{table}: {count}")
        return 0

    if args.command == "db-evaluate":
        limit = args.limit if args.limit and args.limit > 0 else None
        result = run_db_evaluation(
            package,
            dsn=args.database_url,
            version_id=args.version_id,
            retriever_mode=args.retriever,
            limit=limit,
            top_k=args.top_k,
            report_path=args.report,
        )
        print(f"run_id={result.run_id}")
        print(f"retriever={result.retriever}")
        print(f"total={result.total}")
        print(f"top1={result.top1_hits}/{result.total} {result.top1_rate:.2%}")
        print(f"top3={result.top3_hits}/{result.total} {result.top3_rate:.2%}")
        print(f"passed={result.passed}/{result.total} {result.pass_rate:.2%}")
        return 0 if result.top1_rate >= 0.8 else 1

    if args.command == "db-eval-runs":
        runs = latest_eval_runs(dsn=args.database_url, limit=args.limit)
        print(json.dumps(runs, ensure_ascii=False, indent=2))
        return 0

    if args.command == "hybrid-report":
        questions = [
            "数字孪生为什么强调虚实闭环？",
            "道路工程数字化设计经历了哪些主要阶段？",
            "为什么说道路数字化设计不是简单的软件升级？",
            "CAD图元和BIM构件有什么本质区别？",
            "GIS技术在现代道路设计中的主要作用是什么？",
            "以模型为核心的设计流程包括哪些环节？",
        ]
        output = write_hybrid_report(package, questions, args.out, vector_path=args.vectors, model=args.model)
        print(f"hybrid_report={output}")
        return 0

    if args.command == "ask":
        retriever = AnswerRetriever(package)
        hits = retriever.search(args.question, top_k=args.top_k)
        if not hits:
            print("教材知识库未找到直接答案。")
            return 2
        print("Top hits:")
        for idx, hit in enumerate(hits, 1):
            print(f"{idx}. {hit.answer_id} score={hit.score:.2f} reasons={','.join(hit.reasons)}")
        print("\nAnswer:\n")
        print(render_answer(hits[0].card))
        resources = build_bound_resources(package.resources)
        recommended = recommend_resources(hits[0].card, resources)
        if recommended:
            print("\nRecommended resources:")
            for item in recommended:
                print(f"- {item.get('title')} [{item.get('resource_id')}] {item.get('file_path')}")
        return 0

    if args.command == "evaluate":
        limit = args.limit if args.limit and args.limit > 0 else None
        result = evaluate_package(package, limit=limit)
        write_eval_report(result, args.report, args.failures)
        print(f"total={result.total}")
        print(f"top1={result.top1_hits}/{result.total} {result.top1_rate:.2%}")
        print(f"top3={result.top3_hits}/{result.total} {result.top3_rate:.2%}")
        print(f"passed={result.passed}/{result.total} {result.pass_rate:.2%}")
        print(f"report={args.report}")
        print(f"failures={args.failures}")
        return 0 if result.top1_rate >= 0.8 else 1

    if args.command == "resource-evaluate":
        limit = args.limit if args.limit and args.limit > 0 else None
        result = evaluate_resource_questions(
            package,
            limit=limit,
            use_vectors=args.use_vectors,
            use_db=args.use_db,
            database_url=args.database_url,
        )
        write_resource_eval_report(result, args.report, args.failures, chapter_label=infer_chapter_label(package))
        print(f"total={result.total}")
        print(f"top1={result.top1_hits}/{result.total} {result.top1_rate:.2%}")
        print(f"passed={result.passed}/{result.total} {result.pass_rate:.2%}")
        print(f"report={args.report}")
        print(f"failures={args.failures}")
        return 0 if result.pass_rate >= 0.8 else 1

    if args.command == "release":
        result = run_release(
            package,
            processed_dir=args.processed_dir,
            output_dir=args.output_dir,
            database_url=args.database_url,
            model=args.model,
            base_url=args.base_url,
            batch_size=args.batch_size,
            generate_embeddings=args.generate_embeddings,
            apply_db=args.apply_db,
            apply_migration=args.apply_migration,
            db_hybrid_limit=args.db_hybrid_limit,
            min_pass_rate=args.min_pass_rate,
        )
        print(f"chapter_id={result.chapter_id}")
        print(f"version_id={result.version_id}")
        print(f"status={result.status}")
        for step in result.steps:
            print(f"{step.name}: {step.status} - {step.summary}")
        print(f"report={result.report_path}")
        print(f"json={result.json_path}")
        return 0 if result.status in {"ready", "released"} else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
