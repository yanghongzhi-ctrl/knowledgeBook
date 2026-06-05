-- Recommend resources based on answer card related knowledge points.
-- Parameters:
--   :version_id
--   :answer_id
--   :top_k

WITH selected_card AS (
  SELECT answer_id, related_kps, recommended_resources
  FROM answer_cards
  WHERE version_id = :version_id
    AND answer_id = :answer_id
),
card_kps AS (
  SELECT jsonb_array_elements_text(related_kps) AS kp_id
  FROM selected_card
),
explicit_resources AS (
  SELECT jsonb_array_elements_text(recommended_resources) AS resource_id
  FROM selected_card
),
SELECT
  r.resource_id,
  r.resource_type,
  r.title,
  r.file_path,
  r.status,
  (
    CASE WHEN er.resource_id IS NOT NULL THEN 100 ELSE 0 END
    + 25 * COUNT(ck.kp_id)
  ) AS score
FROM resources r
LEFT JOIN explicit_resources er
  ON er.resource_id = r.resource_id
LEFT JOIN card_kps ck
  ON r.related_kps ? ck.kp_id
WHERE r.version_id = :version_id
GROUP BY r.resource_id, r.resource_type, r.title, r.file_path, r.status, er.resource_id
HAVING (
  CASE WHEN er.resource_id IS NOT NULL THEN 100 ELSE 0 END
  + 25 * COUNT(ck.kp_id)
) > 0
ORDER BY score DESC
LIMIT :top_k;
