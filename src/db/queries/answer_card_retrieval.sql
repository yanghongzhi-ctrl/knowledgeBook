-- Answer-card-first retrieval query for PostgreSQL + pgvector.
-- Parameters:
--   :version_id       e.g. 'ch01_kb_v1.0'
--   :question         raw student question
--   :query_embedding  vector(1024), optional when embedding is available
--   :top_k            candidate count

WITH keyword_hits AS (
  SELECT
    ac.answer_id AS object_id,
    'answer_card' AS object_type,
    100.0
      + similarity(ac.canonical_question, :question) * 80
      + COALESCE(MAX(similarity(sq.alias_or_question, :question)) * 60, 0)
      + COALESCE(MAX(rc.retrieval_priority), 0) * 0.1 AS keyword_score
  FROM answer_cards ac
  LEFT JOIN synonym_questions sq
    ON sq.version_id = ac.version_id
   AND sq.target_id = ac.answer_id
  LEFT JOIN rag_config rc
    ON rc.version_id = ac.version_id
   AND rc.object_id = ac.answer_id
   AND rc.object_type = 'answer_card'
  WHERE ac.version_id = :version_id
    AND ac.status = 'checked'
    AND (
      ac.canonical_question % :question
      OR sq.alias_or_question % :question
      OR rc.index_text % :question
    )
  GROUP BY ac.answer_id, ac.canonical_question
),
vector_hits AS (
  SELECT
    ec.source_id AS object_id,
    ec.source_type AS object_type,
    100.0 * (1 - (ec.embedding <=> :query_embedding)) AS vector_score
  FROM embedding_corpus ec
  JOIN rag_config rc
    ON rc.version_id = ec.version_id
   AND rc.object_id = ec.source_id
   AND rc.object_type = ec.source_type
  WHERE ec.version_id = :version_id
    AND ec.source_type = 'answer_card'
    AND ec.embedding IS NOT NULL
    AND rc.primary_output = TRUE
    AND rc.fallback_only = FALSE
  ORDER BY ec.embedding <=> :query_embedding
  LIMIT :top_k
),
merged AS (
  SELECT object_id, object_type, keyword_score, 0.0 AS vector_score FROM keyword_hits
  UNION ALL
  SELECT object_id, object_type, 0.0 AS keyword_score, vector_score FROM vector_hits
),
scored AS (
  SELECT
    object_id,
    object_type,
    SUM(keyword_score) AS keyword_score,
    SUM(vector_score) AS vector_score,
    SUM(keyword_score) * 0.55 + SUM(vector_score) * 0.45 AS final_score
  FROM merged
  GROUP BY object_id, object_type
)
SELECT
  scored.final_score,
  scored.keyword_score,
  scored.vector_score,
  ac.*
FROM scored
JOIN answer_cards ac
  ON ac.answer_id = scored.object_id
WHERE scored.object_type = 'answer_card'
ORDER BY scored.final_score DESC
LIMIT :top_k;

