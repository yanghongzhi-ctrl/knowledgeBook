-- Evidence lookup is allowed only after an Answer_Card has been selected.
-- Source_Chunks must not be used as the student answer body.
-- Parameters:
--   :version_id
--   :section_id
--   :query
--   :top_k

SELECT
  sc.chunk_id,
  sc.heading_path,
  sc.source_excerpt,
  sc.evidence_role,
  sc.usable_for_answer,
  similarity(sc.source_excerpt, :query) AS score
FROM source_chunks sc
WHERE sc.version_id = :version_id
  AND sc.section_id = :section_id
  AND sc.usable_for_answer = 'no_direct_output'
ORDER BY score DESC
LIMIT :top_k;

