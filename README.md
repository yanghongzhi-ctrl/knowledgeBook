# Road Engineering Digital Design KB RAG

This workspace contains the multi-chapter knowledge-base RAG learning system for chapters 1 through 5.

Current implementation uses Python standard library tooling for:

- validating the chapter JSON package;
- exporting processed table JSON files;
- answer-card-first retrieval;
- answer rendering by `answer_mode`;
- QA testset evaluation;
- PostgreSQL + pgvector schema preparation and database-backed retrieval.

Run commands from `D:\knowledgebase`:

```powershell
$env:PYTHONPATH='D:\knowledgebase\src'
py -m pip install -r requirements.txt
py -m kb_rag.cli summary
py -m kb_rag.cli validate
py -m kb_rag.cli export
py -m kb_rag.cli sql-export
py -m kb_rag.cli bind-resources
py -m kb_rag.cli trace
py -m kb_rag.cli quality
py -m kb_rag.cli embed --model bge-m3 --limit 5
py -m kb_rag.cli vector-search "数字孪生为什么强调虚实闭环？"
py -m kb_rag.cli hybrid-ask "数字孪生为什么强调虚实闭环？"
py -m kb_rag.cli db-summary
py -m kb_rag.cli db-vector-search "数字孪生为什么强调虚实闭环？"
py -m kb_rag.cli db-hybrid-ask "数字孪生为什么强调虚实闭环？"
py -m kb_rag.cli db-evaluate --retriever keyword
py -m kb_rag.cli db-evaluate --retriever db-hybrid
py -m kb_rag.cli resource-evaluate
py -m kb_rag.cli release
py -m kb_rag.cli db-eval-runs
py -m kb_rag.cli ask "道路工程数字化设计经历了哪些主要阶段？"
py -m kb_rag.cli evaluate
py -m kb_rag.api --port 8765
```

API examples:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8765/health'
Invoke-RestMethod 'http://127.0.0.1:8765/ask?q=为什么说BIM不是简单的三维模型？'
Invoke-RestMethod 'http://127.0.0.1:8767/ask?q=数字孪生为什么强调虚实闭环？&use_db=true'
Invoke-RestMethod 'http://127.0.0.1:8765/resources'
Invoke-RestMethod 'http://127.0.0.1:8768/answer-card?id=ans_ch01_013'
Invoke-RestMethod 'http://127.0.0.1:8768/eval-runs?limit=5'
Invoke-RestMethod 'http://127.0.0.1:8768/eval-failures?limit=10'
Invoke-RestMethod -Method Post 'http://127.0.0.1:8768/ask' -ContentType 'application/json' -Body '{"question":"图1-1说明了什么？","use_db":true}'
```

Frontend learning assistant:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_dev.ps1
```

Open:

```text
http://127.0.0.1:5174/web/
```

Knowledge-base release workflow:

```powershell
# Local release check without changing PostgreSQL
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release_chapter.ps1 -Chapter ch05

# Full release with embedding rebuild, PostgreSQL import, and database regression
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release_chapter.ps1 -Chapter ch05 -Full
```

Release reports are written to:

```text
output/chXX_rag_engine/reports/release_report_chXX.md
output/chXX_rag_engine/reports/release_report_chXX.json
```

The frontend supports direct question URLs:

```text
http://127.0.0.1:5174/web/?mode=db&q=数字孪生为什么强调虚实闭环？
```

Current frontend learning-assistant capabilities:

- switch keyword, cached-vector, and PostgreSQL/pgvector retrieval;
- view answer, confidence, Top Hits, trace, answer-card detail, related knowledge points, and QA cases;
- open recommended project-local interactive HTML resources;
- answer resource-directed questions such as “这个时间轴脚本应该怎么看？” and “图1-1说明了什么？”;
- preview image resources and show interactive script operation steps in the resource panel;
- review recent persisted evaluation runs and failed cases;
- keep local question history and learning feedback in browser `localStorage`;
- export learning feedback as JSON for knowledge-base maintenance.

Local PostgreSQL/pgvector runtime:

```text
database: postgresql://postgres@127.0.0.1:55432/road_kb
model: bge-m3
embedding dimension: 1024
chapter 1 QA baseline: 443/443 passed
chapter 1 resource-guidance baseline: 65/65 passed
```

The PostgreSQL/pgvector schema is in:

```text
src/db/migrations/001_init_pgvector.sql
```

Chapter 1 review outputs:

```text
output/ch01_rag_engine/reports/chapter1_word_extract.txt
output/ch01_rag_engine/reports/ch01_content_review_enhancement.md
```

Chapter 1 packaged teaching assets:

```text
assets/ch01/interactive_html/
```

The 10 interactive HTML scripts for chapter 1 are copied into the project and referenced by relative paths in JSON and PostgreSQL, so the chapter package can be moved or bundled without depending on the original textbook-material folder.
