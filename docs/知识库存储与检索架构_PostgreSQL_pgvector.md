# 知识库存储与检索架构设计

版本：v0.1  
日期：2026-06-01  
技术路线：JSON 发布包 + PostgreSQL 主存储 + pgvector 向量检索  

## 1. 设计结论

知识维护端继续采用 JSON 发布包，运行端采用 PostgreSQL + pgvector。这样既保留 JSON 易维护、易审校、易版本化的优点，又能获得数据库在查询效率、数据一致性、索引管理、评测记录和后续平台扩展方面的优势。

一期不采用商用数据库、闭源向量库或云端专有服务。所有核心组件优先选择可自托管的开源方案。

## 2. 总体架构

```text
教材 Word / HTML 脚本 / 图片素材
        ↓
章节知识库 JSON 发布包
        ↓
导入器：schema 校验、版本登记、数据入库
        ↓
PostgreSQL 主存储
        ↓
pgvector 向量索引 + PostgreSQL 全文/模糊索引
        ↓
答案卡优先 RAG 服务
        ↓
学习平台 API / AI 问答侧栏 / 自动评测
```

关键原则：

- JSON 是维护发布包，不是长期运行时数据库。
- PostgreSQL 是运行时主存储和事实源。
- pgvector 索引可从 PostgreSQL 主表重建。
- `Answer_Cards` 是主回答来源。
- `Source_Chunks` 只作证据，不作答案主体。
- HTML、图片、视频等大文件只存路径和元数据，不直接存入数据库。

## 3. 开源组件选型

| 能力 | 组件 | 说明 |
|---|---|---|
| 结构化数据库 | PostgreSQL | 主数据、版本、关系、评测、日志 |
| 向量检索 | pgvector | 中小规模教材知识库足够，减少组件复杂度 |
| 模糊检索 | pg_trgm | 标准问题、学生问法、同义词匹配 |
| 全文检索 | PostgreSQL full text | 用于关键词召回和辅助过滤 |
| 对象资源 | 本地文件目录，后续 MinIO | 存 HTML、图片、视频、教材附件 |
| 后端接口 | FastAPI 或 Node.js/TypeScript | 按团队技术栈选择 |
| Embedding | bge-m3 / bge-large-zh / gte 系列 | 本地开源模型，维度按模型确定 |
| Reranker | bge-reranker 系列 | P1/P2 接入，提高 TopK 排序 |

## 4. 数据分层

| 层级 | 数据对象 | 存储方式 | RAG 角色 |
|---|---|---|---|
| 发布层 | 章节 JSON / JSONL | 文件 | 维护、审校、版本发布 |
| 主数据层 | 答案卡、知识点、证据、测试集、资源 | PostgreSQL 表 | 事实源 |
| 检索层 | index_text、embedding | PostgreSQL + pgvector | 召回候选 |
| 资源层 | HTML、图片、视频 | 文件路径/MinIO 路径 | 学习资源推荐 |
| 评测层 | 测试运行、失败样例、trace | PostgreSQL 表 + 报告文件 | 质量闭环 |

## 5. 核心表设计

### 5.1 版本与章节

```sql
CREATE TABLE kb_chapters (
  chapter_id text PRIMARY KEY,
  title text NOT NULL,
  current_version text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE kb_versions (
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
```

### 5.2 答案卡主表

```sql
CREATE TABLE answer_cards (
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
```

### 5.3 知识点与证据

```sql
CREATE TABLE knowledge_points (
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
  key_points jsonb DEFAULT '[]'::jsonb,
  keywords jsonb DEFAULT '[]'::jsonb,
  aliases jsonb DEFAULT '[]'::jsonb,
  common_mistakes jsonb DEFAULT '[]'::jsonb,
  correction_explanation text,
  answer_boundary text,
  source_hint text,
  status text DEFAULT 'draft',
  raw jsonb NOT NULL
);

CREATE TABLE source_chunks (
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
```

### 5.4 检索配置与向量语料

```sql
CREATE TABLE rag_config (
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
  PRIMARY KEY (version_id, object_id, object_type)
);

CREATE TABLE embedding_corpus (
  embedding_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  source_type text NOT NULL,
  source_id text NOT NULL,
  embedding_text text NOT NULL,
  metadata text,
  -- 开发阶段保持维度灵活；生产阶段可在模型确定后改为 vector(1024) 或 vector(768)。
  embedding vector,
  updated_at timestamptz DEFAULT now()
);
```

向量维度由最终 embedding 模型决定。开发阶段使用不固定维度的 `vector`，便于切换 Ollama 本地模型；生产阶段建议固定为实际模型维度并重建向量索引。

### 5.5 评测表

```sql
CREATE TABLE qa_evaluation_testset (
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

CREATE TABLE rag_eval_runs (
  run_id text PRIMARY KEY,
  version_id text NOT NULL REFERENCES kb_versions(version_id),
  started_at timestamptz DEFAULT now(),
  finished_at timestamptz,
  metrics jsonb DEFAULT '{}'::jsonb,
  report_path text
);

CREATE TABLE rag_eval_cases (
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
```

## 6. 索引策略

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_answer_cards_chapter_status
  ON answer_cards (chapter_id, status);

CREATE INDEX idx_answer_cards_question_trgm
  ON answer_cards USING gin (canonical_question gin_trgm_ops);

CREATE INDEX idx_knowledge_points_title_trgm
  ON knowledge_points USING gin (title gin_trgm_ops);

CREATE INDEX idx_rag_config_priority
  ON rag_config (version_id, object_type, retrieval_priority DESC);

CREATE INDEX idx_rag_config_index_text_trgm
  ON rag_config USING gin (index_text gin_trgm_ops);

CREATE INDEX idx_embedding_corpus_source
  ON embedding_corpus (version_id, source_type, source_id);

-- 生成 embedding 后启用，维度和索引类型按数据量调整。
-- CREATE INDEX idx_embedding_corpus_hnsw
--   ON embedding_corpus USING hnsw (embedding vector_cosine_ops);
```

第一章和全书早期阶段数据量小，pgvector 精确检索也能满足需求；全书扩展后再启用 HNSW。

## 7. RAG 检索流程

1. 接收学生问题，确定章节上下文。
2. 对问题做标准化和 embedding。
3. 从 `answer_cards`、`synonym_questions`、`rag_config.index_text` 做关键词/模糊召回。
4. 从 `embedding_corpus` 中优先召回 `answer_card`。
5. 如果答案卡命中不足，再召回 `knowledge_point` 和 `concept_comparison`。
6. 只在证据展示阶段召回 `source_chunk`。
7. 按 `retrieval_priority`、向量相似度、关键词得分、问法命中和章节一致性重排。
8. 选择 Top1 答案卡，按 `answer_mode` 渲染。
9. 检查 `must_include`、`avoid_content` 和输出格式。
10. 写入 trace，用于评测和教师复核。

## 8. 导入发布流程

```text
1. 维护人员提交 ch01_kb_v1.0.json
2. 校验 JSON 顶层表是否齐全
3. 校验 Answer_Cards / Knowledge_Points / QA_Evaluation_Testset 必填字段
4. 计算发布包 checksum
5. 写入 kb_versions
6. 各表批量 upsert
7. 写入 rag_config 和 embedding_corpus
8. 生成 embedding 并更新 pgvector 字段
9. 构建全文/模糊/向量索引
10. 运行 QA_Evaluation_Testset
11. 生成 eval_report_ch01.md
12. 通过后标记版本为 released
```

## 9. 第一章落地优先级

P0：

- 安装 PostgreSQL 和 pgvector。
- 建立核心表和索引。
- 导入第一章完整 JSON。
- 导入 443 条 QA 测试用例。
- 接入本地开源 embedding 模型，为 `Embedding_Corpus.embedding_text` 生成向量。
- 实现答案卡优先检索和评测。

P1：

- 调优 pgvector 相似度检索、TopK 阈值和混合召回权重。
- 接入第一章 10 个 HTML 脚本资源路径。
- 将评测 trace 写入 `rag_eval_cases`。

P2：

- 接入开源 reranker。
- 增加教师复核界面。
- 扩展到第二章及后续章节。
- 后续如资源增多，将文件目录迁移到 MinIO。

## 10. 当前本地落地状态

截至 2026-06-01，第一章样板链路已从“schema 准备”推进到“数据库可检索”：

- 本地运行环境：PostgreSQL 16.10 + pgvector 0.8.1。
- 数据库地址：`postgresql://postgres@127.0.0.1:55432/road_kb`。
- 向量模型：`bge-m3`。
- 向量维度：`vector(1024)`。
- 向量索引：`idx_embedding_corpus_hnsw`，使用 `vector_cosine_ops`。
- 第一章已导入：112 张答案卡、74 个知识点、443 条 QA 测试题、186 条 embedding 语料。
- 已写入向量：186 条。
- 检索适配层：`PgVectorSearcher` + `DbHybridAnswerRetriever`。
- API 开关：`use_db=true`。
- 评测入库：`rag_eval_runs` + `rag_eval_cases` 已接通。

验证命令：

```powershell
$env:PYTHONPATH='D:\knowledgebase\src'
py -m kb_rag.cli db-summary
py -m kb_rag.cli db-vector-search "数字孪生为什么强调虚实闭环？"
py -m kb_rag.cli db-hybrid-ask "数字孪生为什么强调虚实闭环？"
```

松散问法“数字孪生为什么强调虚实闭环？”当前数据库混合检索 Top1 为 `ans_ch01_013`。

数据库已保存两条全量评测基线：

| 检索器 | 测试题 | Top1 | Top3 | 通过率 |
|---|---:|---:|---:|---:|
| keyword | 443 | 100.00% | 100.00% | 100.00% |
| db-hybrid | 443 | 100.00% | 100.00% | 100.00% |

第一章 4 个歧义样例已通过“保留答案卡、改写判别问法”的方式修正，避免将概念精简版答案和综合版答案硬合并。
