# 《道路工程数字化设计》AI知识库学习平台研发计划

版本：v0.2  
日期：2026-06-01  
范围：先完成第一章样板章，再复制到后续章节  
依据材料：
- `C:\Users\yangh\Downloads\道路工程数字化设计教材_AI知识库学习平台研发方案（修订版）.docx`
- `C:\Users\yangh\Downloads\第1章_道路工程数字化设计概述_知识库_v1.0完备版.json`
- `C:\Users\yangh\Downloads\第1章_答案卡与知识点_v1.0完备版.jsonl`
- `C:\Users\yangh\Downloads\Codex指令报告_基于第一章完备知识库的RAG精准问答实现.docx`
- `D:\道路工程数字设计方法\教材脚本`

## 1. 总体落地判断

本项目不应再按“教材 Word 切片库 + 大模型临时总结”的方式推进，而应落地为“答案卡优先的精准 RAG 学习平台”。

第一章的研发目标是先做出可验证的样板章：把 `Answer_Cards` 作为学生问答的主检索层，把 `Knowledge_Points` 作为概念补充层，把 `Source_Chunks` 降级为证据追溯层，把互动脚本作为资源推荐层。第一章样板章通过验收后，再按同一模板扩展到第二章及后续章节。

存储方案采用“JSON 发布维护 + PostgreSQL 主存储 + pgvector 向量检索”的开源技术路线。JSON 仍作为知识维护和版本发布包，平台运行时将发布包导入 PostgreSQL；结构化查询、版本管理、评测记录和资源关系由 PostgreSQL 承担，语义召回由 pgvector 承担。暂不引入商用数据库或闭源检索组件。

## 2. 第一章现有资产盘点

### 2.1 结构化知识库

第一章完整 JSON 是一期主数据源，jsonl 作为答案卡和知识点的轻量导入/向量化辅助文件。完整 JSON 当前包含：

| 表/层 | 数量 | 用途 |
|---|---:|---|
| `README` | 5 | 版本、构建日期和说明 |
| `Chapter_Structure` | 15 | 章节结构、学习目标和导航 |
| `Source_Chunks` | 31 | 原文证据层，只作追溯 |
| `Knowledge_Points` | 74 | 知识点解释和误区纠正 |
| `Answer_Cards` | 112 | 学生问答主检索层 |
| `Concept_Comparison` | 4 | CAD/BIM、BIM/数字孪生等比较表 |
| `Synonyms_Questions` | 922 | 同义词、别名和学生问法扩展 |
| `Knowledge_Relations` | 185 | 知识点关系、推荐和 RAG 扩展 |
| `Resources` | 9 | 图片/脚本等资源占位与推荐 |
| `Exercises` | 5 | 习题、标准答案和评分规则 |
| `QA_Evaluation_Testset` | 443 | 自动评测主测试集 |
| `RAG_Config` | 217 | 检索优先级、主输出和兜底配置 |
| `Embedding_Corpus` | 186 | 向量化语料 |
| `Prompt_Templates` | 5 | 回答模板 |
| `Quality_Checklist` | 6 | 质量检查项 |

第一章 jsonl 当前共 186 条记录，解析无错误：

| 类型 | 数量 | 用途 |
|---|---:|---|
| `knowledge_point` | 74 | 概念解释、误区纠正、工程意义补充 |
| `answer_card` | 112 | 学生问答主来源 |

答案卡题型分布：

| 题型 | 数量 |
|---|---:|
| 概念解释 | 82 |
| 条目列举 | 12 |
| 比较辨析 | 6 |
| 习题答案 | 5 |
| 流程说明 | 3 |
| 原因说明 | 3 |
| 概念辨析 | 1 |

答案输出模式分布：

| 输出模式 | 数量 |
|---|---:|
| `bullet` | 103 |
| `table` | 6 |
| `step` | 3 |

第一章内部小节分布：

| 小节 | 记录数 |
|---|---:|
| `ch01_sec01` | 71 |
| `ch01_sec02` | 60 |
| `ch01_sec03` | 50 |
| `ch01_ex` | 5 |

### 2.2 第一章互动脚本资源

完整 JSON 的 `Resources` 表当前有 9 条资源记录，多数仍为 `placeholder_to_bind`。教材脚本目录实际有 10 个第一章 HTML 互动资源，需要在 P1 阶段完成资源表补全和本地文件路径绑定：

| 文件 | 建议资源类型 | 推荐绑定方向 |
|---|---|---|
| `1.1设计阶段的演进.html` | 时间轴/阶段认知 | CAD、BIM、BIM+GIS、数字孪生阶段演进 |
| `1.2CAD阶段图元语义与设计变更联动.html` | 机制演示 | CAD 图元、工程语义、设计变更局限 |
| `1.3道路BIM概念与特点.html` | 构件/参数演示 | BIM 构件语义、PRR 参数驱动 |
| `1.4BIM+GIS 图层叠加与路线适宜性分析.html` | 空间分析演示 | BIM+GIS、图层叠加、路线适宜性 |
| `1.5数字孪生虚实闭环交互脚本.html` | 虚实闭环演示 | 数字孪生、实时感知、仿真预测 |
| `1.6道路工程数字化设计理念.html` | 理念总览 | 构件化、参数化、数据化、协同化 |
| `1.7道路工程数字化设计技术体系.html` | 技术体系总览 | CAD、BIM、GIS、数字孪生职责分工 |
| `1.8以模型为核心的设计流程.html` | 流程重构演示 | 模型核心、数据贯通、协同交付 |
| `1.9数据驱动的设计控制.html` | 规则校核演示 | 数据驱动、规则校核、几何要素联动 |
| `1.10典型工具软件在各阶段应用模式.html` | 工具链演示 | 工具软件、阶段分工、成果流转 |

一期文本问答先只做资源索引和推荐，不做复杂图像理解或脚本自动评分。

## 3. 第一章样板章交付目标

第一章样板章需要交付 6 类可运行成果：

| 成果 | 说明 | 优先级 |
|---|---|---|
| 知识库导入器 | 读取完整 JSON 和 jsonl，校验字段，导入 PostgreSQL 主表 | P0 |
| 答案卡优先检索器 | 优先检索 `Answer_Cards`，支持全文检索 + pgvector 语义检索 + 规则重排 | P0 |
| RAG 编排器 | 固化 `Answer_Cards -> Knowledge_Points -> Source_Chunks -> Resources` 路由 | P0 |
| 答案模板引擎 | 按 `answer_mode` 输出 bullet/table/step，不直接复制 Word 长段 | P0 |
| 自动评测器 | 检查答案卡命中、必答点覆盖、禁止内容、输出格式 | P0 |
| 第一章资源推荐 | 将答案卡和知识点关联到 10 个互动脚本 | P1 |

## 4. 技术实现边界

### 4.1 一期必须实现

- 以第一章完整 JSON 作为问答、证据、评测和资源配置主输入。
- 以第一章 jsonl 作为轻量导入、调试和向量化辅助输入。
- 使用 PostgreSQL 存储章节知识库主数据、版本、关系、资源和评测结果。
- 使用 pgvector 存储 `Embedding_Corpus` 向量，建立答案卡、知识点和证据的分层向量索引。
- 保留教材 Word 和脚本目录的路径索引，但不得把 Word 长段作为学生答案主体。
- 支持第一章内教材问答、概念解释、阶段列举、比较辨析、流程说明、习题答案。
- 输出时必须使用答案卡中的 `answer_points` 作为骨架。
- 必须检查 `must_include` 和 `avoid_content`。
- 低置信度时提示“教材知识库未找到直接答案”，再给有限补充。
- 生成第一章自动评测报告。

### 4.2 一期暂不实现

- 全书知识库一次性导入。
- 复杂用户权限、班级管理和 LMS 对接。
- 图片内容自动理解和脚本交互过程自动评分。
- 大模型微调。
- 跨章综合问答的正式上线。

## 4.3 开源存储与检索架构

一期正式采用以下开源组件：

| 能力 | 组件 | 定位 |
|---|---|---|
| 结构化主存储 | PostgreSQL | 存储章节、版本、答案卡、知识点、证据、测试集、资源和日志 |
| 向量检索 | pgvector | 存储 embedding，支持答案卡、知识点和证据分层召回 |
| 全文/关键词检索 | PostgreSQL full text + trigram | 支持标准问题、学生问法、同义词和关键词召回 |
| 文件资源 | 本地目录，后续可换 MinIO | 存 HTML 脚本、图片、视频和教材附件 |
| 维护发布 | JSON 发布包 | 教师/知识库团队维护与版本发布入口 |

运行链路：

```text
章节 JSON 发布包
  -> 导入器校验 schema
  -> PostgreSQL 主表
  -> embedding 生成与 pgvector 入库
  -> 全文索引/向量索引构建
  -> RAG 问答与 QA 自动评测
```

数据库是运行时事实源；JSON 是维护端发布包。索引和 embedding 可以从 PostgreSQL 主数据重建，不作为唯一事实源。

## 5. 推荐工程目录

建议在工作区内建立如下目录：

```text
D:\knowledgebase\
  data\
    raw\
      ch01\
        第1章_道路工程数字化设计概述_知识库_v1.0完备版.json
        第1章_答案卡与知识点_v1.0完备版.jsonl
    processed\
      ch01\
        answer_cards.json
        knowledge_points.json
        source_chunks.json
        qa_evaluation_testset.json
        rag_config.json
        resource_index.json
  src\
    kb\
      import_chapter.py 或 import_chapter.ts
      validate_schema.py 或 validate_schema.ts
      db_schema.sql
      build_indexes.py 或 build_indexes.ts
    rag\
      retrieve.py 或 retrieve.ts
      orchestrate.py 或 orchestrate.ts
      render_answer.py 或 render_answer.ts
    db\
      migrations\
        001_init_pgvector.sql
    eval\
      evaluate_chapter.py 或 evaluate_chapter.ts
  output\
    ch01_rag_engine\
      reports\
        eval_report_ch01.md
        failed_cases_ch01.json
        rag_trace_samples_ch01.json
  docs\
    第1章_RAG精准问答研发计划.md
```

语言可按现有团队栈选择。若从零开始，建议先用 Python/FastAPI 或 Node.js/TypeScript 快速实现样板章；数据库层统一采用 PostgreSQL + pgvector，避免后续从文件检索迁移到数据库时返工。

## 6. 数据模型落地

### 6.1 PostgreSQL 核心表

第一章完整 JSON 的各层对象映射为 PostgreSQL 表。字段中数组和结构化属性优先使用 `jsonb`，用于保留发布包原貌；高频过滤字段单独列出，便于索引和查询。

| 表名 | 来源 | 关键字段 | 说明 |
|---|---|---|---|
| `kb_chapters` | `README` / `Chapter_Structure` | `chapter_id`、`title`、`current_version` | 章节主表 |
| `kb_versions` | `README` | `version_id`、`chapter_id`、`version`、`build_date`、`source_file`、`status` | 章节知识库版本 |
| `chapter_structure` | `Chapter_Structure` | `node_id`、`parent_id`、`level`、`title`、`summary` | 学习目标和章节结构 |
| `answer_cards` | `Answer_Cards` | `answer_id`、`version_id`、`section_id`、`canonical_question`、`question_type`、`answer_mode`、`answer_points jsonb`、`must_include jsonb`、`avoid_content jsonb`、`status` | 问答主检索层 |
| `knowledge_points` | `Knowledge_Points` | `kp_id`、`version_id`、`section_id`、`title`、`knowledge_type`、`definition`、`key_points jsonb`、`keywords jsonb`、`status` | 概念和知识点解释 |
| `source_chunks` | `Source_Chunks` | `chunk_id`、`version_id`、`section_id`、`heading_path`、`source_excerpt`、`usable_for_answer` | 教材证据层 |
| `concept_comparisons` | `Concept_Comparison` | `comparison_id`、`title`、`dimensions`、`related_answer_cards` | 比较辨析 |
| `synonym_questions` | `Synonyms_Questions` | `synonym_id`、`alias_or_question`、`target_id`、`type`、`priority` | 同义词和学生问法 |
| `knowledge_relations` | `Knowledge_Relations` | `relation_id`、`source_id`、`relation_type`、`target_id`、`weight` | 知识关系和推荐 |
| `resources` | `Resources` | `resource_id`、`resource_type`、`title`、`file_path`、`related_kps`、`status` | 图片、脚本、视频资源索引 |
| `exercises` | `Exercises` | `exercise_id`、`question`、`standard_answer_points jsonb`、`grading_rubric`、`expected_answer_card` | 习题和评分 |
| `qa_evaluation_testset` | `QA_Evaluation_Testset` | `test_id`、`question`、`expected_answer_card`、`expected_answer_points jsonb`、`required_response_mode` | 自动评测集 |
| `rag_config` | `RAG_Config` | `object_id`、`object_type`、`retrieval_priority`、`index_text`、`primary_output`、`fallback_only` | 检索控制 |
| `embedding_corpus` | `Embedding_Corpus` | `embedding_id`、`source_type`、`source_id`、`embedding_text`、`metadata`、`embedding vector` | pgvector 向量语料 |
| `prompt_templates` | `Prompt_Templates` | `template_id`、`name`、`trigger`、`template` | 回答模板 |
| `quality_checklist` | `Quality_Checklist` | `check_id`、`item`、`criterion`、`status` | 质量检查 |
| `rag_eval_runs` | 系统生成 | `run_id`、`version_id`、`started_at`、`metrics jsonb` | 评测运行记录 |
| `rag_eval_cases` | 系统生成 | `run_id`、`test_id`、`actual_answer_id`、`passed`、`trace jsonb` | 单题评测结果 |

### 6.2 pgvector 索引分层

`embedding_corpus` 中保留统一向量表，但检索时按 `source_type` 和 `rag_config` 分层：

| 索引层 | 数据范围 | 用途 | 检索限制 |
|---|---|---|---|
| `primary_answer_index` | `source_type='answer_card'` | 主回答召回 | 必须优先检索 |
| `concept_index` | `source_type in ('knowledge_point','concept_comparison')` | 概念补充、误区纠正、比较说明 | 不能替代高置信度答案卡 |
| `evidence_index` | `source_type='source_chunk'` | 教材依据和追溯 | `fallback_only=true`，禁止作为答案主体 |

第一章规模较小，pgvector 可先使用精确向量距离查询或 HNSW 索引；全书扩展后再根据数据量选择 HNSW/IVFFlat 参数。

建议关键索引：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_answer_cards_question_trgm
  ON answer_cards USING gin (canonical_question gin_trgm_ops);

CREATE INDEX idx_synonym_questions_alias_trgm
  ON synonym_questions USING gin (alias_or_question gin_trgm_ops);

CREATE INDEX idx_rag_config_object
  ON rag_config (object_type, object_id, retrieval_priority DESC);

CREATE INDEX idx_embedding_corpus_source
  ON embedding_corpus (source_type, source_id);

-- 向量维度按最终 embedding 模型确定，例如 1024 或 768。
-- CREATE INDEX idx_embedding_corpus_hnsw
--   ON embedding_corpus USING hnsw (embedding vector_cosine_ops);
```

### 6.3 第一章最小数据对象

`AnswerCard`

| 字段 | 要求 |
|---|---|
| `answer_id` | 主键 |
| `chapter_id` / `section_id` | 章节定位 |
| `canonical_question` | 标准问题 |
| `student_question_patterns` | 问法扩展 |
| `question_type` | 题型识别 |
| `answer_mode` | `bullet` / `table` / `step` / `paragraph` |
| `answer_points` | 主要输出骨架 |
| `concise_answer` / `expanded_answer` | 短答和展开 |
| `must_include` | 必答点检查 |
| `avoid_content` | 禁止内容检查 |
| `evidence_chunks` / `source_excerpt` | 证据追溯 |
| `recommended_resources` | 资源推荐 |
| `answer_boundary` | 回答边界 |
| `confidence_rule` | 置信度规则 |

`KnowledgePoint`

| 字段 | 要求 |
|---|---|
| `kp_id` | 主键 |
| `title` | 知识点标题 |
| `knowledge_type` | 概念类型 |
| `definition` | 概念定义 |
| `core_explanation` | 核心解释 |
| `key_points` | 补充要点 |
| `common_mistakes` | 常见误区 |
| `correction_explanation` | 纠偏说明 |
| `source_hint` | 教材依据提示 |

`ResourceIndex`

| 字段 | 要求 |
|---|---|
| `resource_id` | 主键，如 `ch01_script_timeline` |
| `chapter_id` / `section_id` | 章节定位 |
| `title` | 资源标题 |
| `file_path` | 本地 HTML 路径 |
| `related_kps` | 关联知识点 |
| `related_answer_cards` | 关联答案卡 |
| `qa_use` | 推荐场景 |

`QAEvaluationCase`

| 字段 | 要求 |
|---|---|
| `test_id` | 主键 |
| `question` | 测试问题 |
| `expected_answer_card` | 预期命中答案卡 |
| `expected_kps` | 预期关联知识点 |
| `expected_answer_points` | 预期必答点 |
| `should_not_include` | 禁止内容 |
| `required_response_mode` | 必须输出模式 |
| `pass_rule` | 通过规则 |

`RAGConfig`

| 字段 | 要求 |
|---|---|
| `object_id` | 对象 ID |
| `object_type` | answer_card / knowledge_point / source_chunk 等 |
| `retrieval_priority` | 检索优先级 |
| `index_text` | 索引文本 |
| `answer_mode` | 输出模式 |
| `allow_ai_extension` | 是否允许有限扩展 |
| `need_citation` | 是否需要证据 |
| `primary_output` | 是否可作为主回答来源 |
| `fallback_only` | 是否只可兜底 |

### 6.2 校验规则

导入时必须检查：

- `answer_card` 必须包含 `answer_id`、`canonical_question`、`answer_mode`、`answer_points`、`must_include`、`avoid_content`。
- `knowledge_point` 必须包含 `kp_id`、`title`、`definition`、`key_points`。
- `answer_points` 不得为空。
- `must_include` 至少 1 项。
- `answer_mode=table` 的答案卡必须在渲染层转换为比较表。
- `status` 不是 `checked` 的记录不得默认发布。
- `Source_Chunks.usable_for_answer=no_direct_output` 的内容不得作为答案主体。
- `RAG_Config.fallback_only=true` 的对象不得进入主检索输出。

## 7. 检索与编排策略

### 7.1 检索优先级

固定顺序：

```text
Answer_Cards -> Knowledge_Points -> Concept_Comparison -> Exercises -> Source_Chunks -> Resources
```

第一章完整 JSON 已包含 31 条 `Source_Chunks`，一期即可接入证据索引，但只能用于短依据、引用和追溯，不能作为学生答案主体。

### 7.2 PostgreSQL + pgvector 混合召回算法

第一版直接实现数据库混合召回，关键词召回和向量召回并行计算，再按 `RAG_Config` 重排：

1. 标准化问题：去标点、统一大小写、提取中文关键词。
2. 关键词召回：从 `answer_cards`、`synonym_questions`、`rag_config.index_text` 中召回候选。
3. 向量召回：用问题 embedding 在 `embedding_corpus` 中分层召回。
4. 候选合并：按 `object_id` 合并关键词分、向量分、同义词分和章节上下文分。
5. 重排规则：
   - `Answer_Cards` 的基础优先级最高，使用 `rag_config.retrieval_priority=100`。
   - `Knowledge_Points` 只在答案卡置信度不足或需要补充解释时进入上下文。
   - `Source_Chunks` 只在生成证据依据时读取，不能生成答案主体。
   - `fallback_only=true` 的对象只允许低置信度兜底。
6. 打分参考：
   - 命中标准问题：+100
   - 命中学生问法/同义问法：+80
   - 向量 TopK 相似：按相似度归一化加权
   - 命中标题关键词或必答点：+30
   - 命中相关知识点标题：+20
   - 章节上下文一致：+10
7. Top1 高于阈值时直接按答案卡生成。
8. Top1 不足但 Top3 有相关候选时，给出澄清式回答和候选主题。
9. 无候选时提示“教材知识库未找到直接答案”。

后续可接入开源 Reranker 模型，对 Top20 候选做二次排序，但不改变答案卡优先原则。

### 7.3 回答生成规则

| 问题类型 | 输出要求 |
|---|---|
| 概念解释 | 先给定义，再分条解释工程意义或误区 |
| 条目列举 | 编号条目，优先使用 `answer_points` |
| 比较辨析 | 表格输出，最后补充常见误区 |
| 流程说明 | 按步骤输出，指出输入、处理、输出或关键控制点 |
| 原因说明 | 分条列出原因，最后用一句话概括 |
| 习题答案 | 给出标准答案、评分点、缺失点和复习建议 |

硬性限制：

- 禁止直接输出 Word 原文长段。
- 禁止把 Source_Chunks 排在 Answer_Cards 之前。
- 禁止把 BIM 简化为“三维模型”。
- 禁止把 GIS 简化为“地图显示”。
- 禁止把数字孪生等同于 BIM。
- 禁止加入第一章未涉及的软件操作细节。

## 8. 自动评测设计

完整 JSON 已包含 `QA_Evaluation_Testset` 443 条，正式验收以这 443 条为主；同时可继续从 112 张答案卡生成补充回归问题。

### 8.1 测试用例来源

- 每张答案卡的 `canonical_question`。
- 每张答案卡的 `student_question_patterns`。
- 针对 6 张表格类答案卡构造比较类问法。
- 针对 3 张流程类答案卡构造步骤类问法。
- 针对 5 张习题答案卡构造批改类问法。

### 8.2 指标阈值

| 指标 | 第一章样板章验收阈值 |
|---|---:|
| 答案卡 Top1 命中率 | ≥80% |
| 答案卡 Top3 命中率 | ≥95% |
| 必答点覆盖率 | ≥90% |
| 禁止内容命中率 | ≤5% |
| 条目化/表格化/步骤化格式合格率 | ≥90% |
| 证据追溯可用率 | ≥95% |
| 资源推荐准确率 | 一期抽检 ≥80%，二期 ≥85% |

### 8.3 评测报告字段

`eval_report_ch01.md` 应包含：

- 测试问题总数。
- Top1 / Top3 命中率。
- 按题型统计的命中率。
- 必答点覆盖率。
- 失败样例列表。
- 高风险答案卡列表。
- 推荐修订动作。

`failed_cases_ch01.json` 应包含：

- `question`
- `expected_answer_id`
- `actual_answer_id`
- `score`
- `missing_must_include`
- `unexpected_avoid_content`
- `format_error`
- `fix_suggestion`

## 9. 第一章研发排期

### 第 1 周：样板章数据与检索闭环

| 天 | 任务 | 交付 |
|---|---|---|
| D1 | 建立目录、复制第一章完整 JSON 和 jsonl、定义 schema | `data/raw/ch01`、schema 文档 |
| D2 | 初始化 PostgreSQL + pgvector，建立核心表 | `001_init_pgvector.sql` |
| D3 | 实现完整 JSON 导入器和字段校验 | 第一章数据入库报告 |
| D4 | 接入开源 embedding 模型，生成向量并实现全文检索 + pgvector 分层召回 | `retrieve` 模块 |
| D5 | 实现答案模板渲染并打通命令行问答 | 20 条人工样例通过 |

### 第 2 周：评测、证据和资源推荐

| 天 | 任务 | 交付 |
|---|---|---|
| D6 | 导入 443 条正式 QA 测试集，并生成补充回归测试集 | `qa_evaluation_testset` 表、`qa_eval_ch01_generated.json` |
| D7 | 实现自动评测器，评测结果写入数据库 | `eval_report_ch01.md`、`rag_eval_runs` |
| D8 | 接入 10 个互动脚本资源索引 | `resources` 表 |
| D9 | 增加答案审查：必答点、禁止内容、低置信度 | 审查日志 |
| D10 | 修订失败答案卡和召回权重 | 第一章样板章 v1.0 |

### 第 3 周：API 和教师复核准备

| 天 | 任务 | 交付 |
|---|---|---|
| D11 | 封装问答 API | `/api/chapter/ch01/ask` |
| D12 | 封装评测 API | `/api/chapter/ch01/evaluate` |
| D13 | 输出 trace：检索候选、命中卡、模板、证据 | `rag_trace_samples_ch01.json` |
| D14 | 设计教师复核数据格式 | 失败样例复核表 |
| D15 | 第一章验收评审 | 验收报告和后续章模板 |

## 10. 角色分工

| 角色 | 第一章任务 |
|---|---|
| 课程负责人 | 确认答案边界、必答点、禁止扩展内容、失败样例修订意见 |
| 知识库工程师 | 完整 JSON/jsonl 导入、schema 校验、答案卡修订、资源关系维护 |
| 后端工程师 | 检索服务、RAG 编排、评测服务、API |
| 前端工程师 | 后续阅读器、AI 侧栏、资源推荐入口、教师复核界面 |
| 模型工程师 | 一期接入开源 embedding 模型；后续接入 Reranker/LLM 并优化推理性能 |
| 测试人员 | 维护 QA 测试集、回归测试、失败案例归因 |

## 11. 后续章节扩展规则

第一章验收后，第二章开始不再走简单 Word 切片流程，而是直接按第一章模板建设：

1. 从教材章节和互动脚本抽取 `Chapter_Structure`。
2. 建立 `Knowledge_Points`，每节覆盖核心概念、方法、流程、误区。
3. 为高频问题建立 `Answer_Cards`，必须包含 `answer_points`、`must_include`、`avoid_content`。
4. 为比较类内容建立 `Concept_Comparison` 或 table 型答案卡。
5. 为习题建立 `Exercises` 和评分点。
6. 为每章生成不少于 80 条 QA 测试问题。
7. 通过章节验收后发布 `chXX_kb_v1.0`。
8. 再接入该章图片、HTML 脚本、视频等资源关系。

建议扩展顺序：

| 阶段 | 范围 | 目标 |
|---|---|---|
| 样板章 | 第 1 章 | 固化数据模型、检索逻辑、评测流程 |
| 第二批 | 第 2-4 章 | 覆盖几何建模、CAD、BIM 基础，验证不同知识类型 |
| 第三批 | 第 5-9 章 | 覆盖 GIS、软件流程、BIM+GIS 集成，强化资源推荐 |
| 第四批 | 第 10-11 章 | 覆盖 AI 和数字孪生，验证综合问答和跨章关系 |

## 12. 决策点

需要尽早确认 4 个研发决策：

| 决策 | 建议 |
|---|---|
| 后端语言 | 样板章可先用 Python/FastAPI 或 Node.js/TypeScript，按团队熟悉度定 |
| 向量库 | 一期采用 PostgreSQL + pgvector；暂不引入独立向量库 |
| LLM 接口 | 采用 OpenAI 兼容接口，便于本地中文模型替换 |
| 知识库主格式 | JSON/JSONL 作为维护发布包；PostgreSQL 作为运行时主存储 |

## 13. 第一章立即执行清单

P0：

- 建立 `data/raw/ch01` 并放入第一章完整 JSON 和 jsonl。
- 定义 PostgreSQL 表结构和 JSON schema。
- 初始化 PostgreSQL + pgvector。
- 实现完整 JSON 导入、字段校验和入库报告。
- 接入开源 embedding 模型，生成 `Embedding_Corpus` 向量。
- 实现答案卡优先的全文检索 + pgvector 混合召回。
- 实现 `bullet`、`table`、`step` 三种模板。
- 导入 `QA_Evaluation_Testset` 443 条正式测试用例。
- 生成基于答案卡的补充自动评测问题。
- 输出 `eval_report_ch01.md`。

P1：

- 接入 10 个 HTML 互动脚本资源索引。
- 将 JSON 中 9 条 `Resources` 占位资源与本地脚本/图片路径完成绑定，并补齐缺失脚本资源。
- 在回答末尾推荐相关脚本资源。
- 输出检索 trace，支持教师复核。
- 增加失败案例修订表。

P2：

- 接入开源 Reranker，提高 TopK 候选排序质量。
- 开发教师后台原型。
- 优化 Source_Chunks 证据引用和教材依据展示。
- 扩展到第二章。

## 14. 第一章验收口径

第一章可以进入后续章节扩展的条件：

- 自动评测报告生成成功。
- Top1 命中率达到 80% 以上，Top3 命中率达到 95% 以上。
- 核心题必答点覆盖率达到 90% 以上。
- 没有直接复制 Word 长段作为学生答案的样例。
- BIM、GIS、数字孪生三个高风险概念无明显误导。
- 10 个互动脚本能被索引，并能在相关问题后被推荐。
- 教师抽检样例通过率达到 85% 以上。
