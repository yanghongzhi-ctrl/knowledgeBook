CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS kb_chapters (
  chapter_id text PRIMARY KEY,
  title text NOT NULL,
  current_version text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kb_versions (
  version_id text PRIMARY KEY,
  chapter_id text NOT NULL REFERENCES kb_chapters(chapter_id),
  version text NOT NULL,
  build_date date,
  source_file text NOT NULL,
  source_checksum text,
  status text NOT NULL DEFAULT 'draft',
  raw_metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chapter_structure (
  node_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  parent_id text,
  level text NOT NULL,
  title text NOT NULL,
  learning_role text,
  summary text,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS answer_cards (
  answer_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  chapter_id text NOT NULL,
  section_id text,
  canonical_question text NOT NULL,
  question_type text,
  student_question_patterns jsonb DEFAULT '[]'::jsonb,
  related_kps jsonb DEFAULT '[]'::jsonb,
  answer_mode text NOT NULL,
  answer_points jsonb NOT NULL,
  concise_answer text,
  expanded_answer text,
  must_include jsonb DEFAULT '[]'::jsonb,
  avoid_content jsonb DEFAULT '[]'::jsonb,
  evidence_chunks jsonb,
  source_excerpt text,
  answer_boundary text,
  recommended_resources jsonb DEFAULT '[]'::jsonb,
  confidence_rule text,
  status text DEFAULT 'draft',
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_points (
  kp_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  chapter_id text NOT NULL,
  section_id text,
  title text NOT NULL,
  knowledge_type text,
  importance text,
  difficulty text,
  definition text,
  core_explanation text,
  plain_explanation text,
  engineering_meaning text,
  application_scenario text,
  key_points jsonb DEFAULT '[]'::jsonb,
  keywords jsonb DEFAULT '[]'::jsonb,
  aliases jsonb DEFAULT '[]'::jsonb,
  related_kps jsonb DEFAULT '[]'::jsonb,
  common_mistakes jsonb DEFAULT '[]'::jsonb,
  correction_explanation text,
  answer_strategy text,
  answer_boundary text,
  source_hint text,
  status text DEFAULT 'draft',
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS source_chunks (
  chunk_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  chapter_id text NOT NULL,
  section_id text,
  heading_path text,
  content_type text,
  evidence_role text,
  source_excerpt text NOT NULL,
  keywords jsonb DEFAULT '[]'::jsonb,
  usable_for_answer text DEFAULT 'no_direct_output',
  review_status text,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS concept_comparisons (
  comparison_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  title text NOT NULL,
  chapter_id text NOT NULL,
  dimensions text,
  answer_use text,
  related_answer_cards text,
  status text DEFAULT 'draft',
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS synonym_questions (
  synonym_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  standard_term text,
  alias_or_question text NOT NULL,
  type text,
  target_id text NOT NULL,
  priority int DEFAULT 0,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_relations (
  relation_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  source_id text NOT NULL,
  relation_type text NOT NULL,
  target_id text NOT NULL,
  weight numeric DEFAULT 1,
  description text,
  use_in_recommendation boolean DEFAULT false,
  use_in_rag boolean DEFAULT false,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS resources (
  resource_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  chapter_id text NOT NULL,
  resource_type text,
  title text NOT NULL,
  file_path text,
  description text,
  related_kps jsonb DEFAULT '[]'::jsonb,
  teaching_use text,
  qa_use text,
  status text DEFAULT 'draft',
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS interactive_scripts (
  script_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  resource_id text NOT NULL REFERENCES resources(resource_id),
  chapter_id text NOT NULL,
  title text NOT NULL,
  file_path text,
  interaction_theme text,
  display_objects jsonb DEFAULT '[]'::jsonb,
  operation_steps jsonb DEFAULT '[]'::jsonb,
  trigger_questions jsonb DEFAULT '[]'::jsonb,
  related_kps jsonb DEFAULT '[]'::jsonb,
  extracted_labels jsonb DEFAULT '[]'::jsonb,
  status text DEFAULT 'draft',
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS exercises (
  exercise_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  chapter_id text NOT NULL,
  question text NOT NULL,
  question_type text,
  related_kps jsonb DEFAULT '[]'::jsonb,
  standard_answer_points jsonb DEFAULT '[]'::jsonb,
  grading_rubric text,
  common_mistakes text,
  feedback_template text,
  expected_answer_card text,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_evaluation_testset (
  test_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  question text NOT NULL,
  expected_answer_card text,
  expected_kps jsonb DEFAULT '[]'::jsonb,
  expected_answer_points jsonb DEFAULT '[]'::jsonb,
  should_not_include jsonb DEFAULT '[]'::jsonb,
  required_response_mode text,
  pass_rule text,
  error_reason text,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_evaluation_testset (
  test_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  chapter_id text NOT NULL,
  question text NOT NULL,
  expected_resource_id text NOT NULL REFERENCES resources(resource_id),
  expected_resource_type text,
  expected_answer_mode text,
  related_kps jsonb DEFAULT '[]'::jsonb,
  resource_intent text,
  pass_rule text,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_config (
  object_id text NOT NULL,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  object_type text NOT NULL,
  retrieval_priority int NOT NULL DEFAULT 0,
  index_text text NOT NULL,
  answer_mode text,
  allow_ai_extension text DEFAULT 'limited',
  need_citation boolean DEFAULT true,
  primary_output boolean DEFAULT false,
  fallback_only boolean DEFAULT false,
  notes text,
  raw jsonb DEFAULT '{}'::jsonb,
  PRIMARY KEY (version_id, object_id, object_type)
);

CREATE TABLE IF NOT EXISTS embedding_corpus (
  embedding_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  source_type text NOT NULL,
  source_id text NOT NULL,
  embedding_text text NOT NULL,
  metadata text,
  -- bge-m3 embeddings produced by Ollama are 1024-dimensional.
  embedding vector(1024),
  updated_at timestamptz DEFAULT now(),
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_templates (
  template_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  name text NOT NULL,
  trigger text,
  template text NOT NULL,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_checklist (
  check_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  item text NOT NULL,
  criterion text,
  status text,
  raw jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_eval_runs (
  run_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  started_at timestamptz DEFAULT now(),
  finished_at timestamptz,
  metrics jsonb DEFAULT '{}'::jsonb,
  report_path text
);

CREATE TABLE IF NOT EXISTS rag_eval_cases (
  run_id text NOT NULL REFERENCES rag_eval_runs(run_id),
  test_id text NOT NULL REFERENCES qa_evaluation_testset(test_id),
  expected_answer_card text,
  actual_answer_card text,
  passed boolean,
  score numeric,
  missing_points jsonb DEFAULT '[]'::jsonb,
  unexpected_content jsonb DEFAULT '[]'::jsonb,
  trace jsonb DEFAULT '{}'::jsonb,
  PRIMARY KEY (run_id, test_id)
);

CREATE INDEX IF NOT EXISTS idx_answer_cards_chapter_status
  ON answer_cards (chapter_id, status);

CREATE INDEX IF NOT EXISTS idx_answer_cards_question_trgm
  ON answer_cards USING gin (canonical_question gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_knowledge_points_title_trgm
  ON knowledge_points USING gin (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_synonym_questions_alias_trgm
  ON synonym_questions USING gin (alias_or_question gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_rag_config_priority
  ON rag_config (version_id, object_type, retrieval_priority DESC);

CREATE INDEX IF NOT EXISTS idx_rag_config_index_text_trgm
  ON rag_config USING gin (index_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_resources_related_kps
  ON resources USING gin (related_kps);

CREATE INDEX IF NOT EXISTS idx_interactive_scripts_resource
  ON interactive_scripts (resource_id);

CREATE INDEX IF NOT EXISTS idx_interactive_scripts_triggers
  ON interactive_scripts USING gin (trigger_questions);

CREATE INDEX IF NOT EXISTS idx_resource_eval_expected_resource
  ON resource_evaluation_testset (expected_resource_id);

CREATE INDEX IF NOT EXISTS idx_embedding_corpus_source
  ON embedding_corpus (version_id, source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_embedding_corpus_hnsw
  ON embedding_corpus USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_rag_eval_cases_passed
  ON rag_eval_cases (run_id, passed);

CREATE INDEX IF NOT EXISTS idx_rag_eval_cases_actual
  ON rag_eval_cases (actual_answer_card);
