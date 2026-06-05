-- Summarize recent persisted RAG evaluation runs.
-- Parameters:
--   :limit

SELECT
  r.run_id,
  r.version_id,
  r.started_at,
  r.finished_at,
  r.metrics ->> 'retriever' AS retriever,
  (r.metrics ->> 'total')::int AS total,
  (r.metrics ->> 'top1_hits')::int AS top1_hits,
  (r.metrics ->> 'top1_rate')::numeric AS top1_rate,
  (r.metrics ->> 'top3_hits')::int AS top3_hits,
  (r.metrics ->> 'top3_rate')::numeric AS top3_rate,
  (r.metrics ->> 'passed')::int AS passed,
  (r.metrics ->> 'pass_rate')::numeric AS pass_rate,
  r.report_path
FROM rag_eval_runs r
ORDER BY r.started_at DESC
LIMIT :limit;
