-- List failed cases for a persisted RAG evaluation run.
-- Parameters:
--   :run_id

SELECT
  c.test_id,
  q.question,
  c.expected_answer_card,
  c.actual_answer_card,
  c.score,
  c.missing_points,
  c.unexpected_content,
  c.trace -> 'top_hits' AS top_hits,
  c.trace -> 'extra' AS extra_trace
FROM rag_eval_cases c
JOIN qa_evaluation_testset q
  ON q.test_id = c.test_id
WHERE c.run_id = :run_id
  AND c.passed IS NOT TRUE
ORDER BY c.test_id;
