# PostgreSQL + pgvector 部署与导入说明

版本：v0.2  
日期：2026-06-01  

## 1. 前置条件

推荐使用项目内 Micromamba 环境安装，避免注册 Windows 系统服务：

```powershell
winget install --id Mamba.Micromamba --silent --accept-source-agreements --accept-package-agreements
$mm='C:\Users\yangh\AppData\Local\Microsoft\WinGet\Packages\Mamba.Micromamba_Microsoft.Winget.Source_8wekyb3d8bbwe\micromamba.exe'
& $mm create -y -p 'D:\knowledgebase\.mamba\pgvector' -c conda-forge postgresql=16 pgvector
```

当前本机已完成：

- PostgreSQL 16.10
- pgvector 0.8.1
- pg_trgm 扩展
- 本地数据目录：`D:\knowledgebase\.pgdata`
- 监听地址：`127.0.0.1:55432`
- 数据库：`road_kb`

当前工作区已准备：

- 建表迁移：[001_init_pgvector.sql](D:/knowledgebase/src/db/migrations/001_init_pgvector.sql)
- 第一章种子数据：[ch01_seed.sql](D:/knowledgebase/output/ch01_rag_engine/db_load/ch01_seed.sql)
- 检索 SQL：[answer_card_retrieval.sql](D:/knowledgebase/src/db/queries/answer_card_retrieval.sql)

## 2. 启动数据库

```powershell
$env:Path='D:\knowledgebase\.mamba\pgvector\Library\bin;' + $env:Path

if (-not (Test-Path 'D:\knowledgebase\.pgdata\PG_VERSION')) {
  initdb -D 'D:\knowledgebase\.pgdata' -U postgres --encoding=UTF8 --auth=trust
}

pg_ctl -D 'D:\knowledgebase\.pgdata' -o '-p 55432' -l 'D:\knowledgebase\.pgdata\postgres.log' start
```

检查状态：

```powershell
pg_ctl -D 'D:\knowledgebase\.pgdata' status
```

## 3. 导入顺序

```powershell
createdb -h 127.0.0.1 -p 55432 -U postgres road_kb
psql -h 127.0.0.1 -p 55432 -U postgres -d road_kb -v ON_ERROR_STOP=1 -f D:\knowledgebase\src\db\migrations\001_init_pgvector.sql
psql -h 127.0.0.1 -p 55432 -U postgres -d road_kb -v ON_ERROR_STOP=1 -f D:\knowledgebase\output\ch01_rag_engine\db_load\ch01_seed.sql
psql -h 127.0.0.1 -p 55432 -U postgres -d road_kb -v ON_ERROR_STOP=1 -f D:\knowledgebase\output\ch01_rag_engine\db_load\ch01_embedding_updates.sql
```

导入后检查：

```sql
SELECT count(*) FROM answer_cards;
SELECT count(*) FROM knowledge_points;
SELECT count(*) FROM source_chunks;
SELECT count(*) FROM qa_evaluation_testset;
SELECT count(*) FROM embedding_corpus;
SELECT source_type, count(*), min(vector_dims(embedding)), max(vector_dims(embedding))
FROM embedding_corpus
GROUP BY source_type;
```

期望第一章：

| 表 | 数量 |
|---|---:|
| `answer_cards` | 112 |
| `knowledge_points` | 74 |
| `source_chunks` | 31 |
| `qa_evaluation_testset` | 443 |
| `embedding_corpus` | 186 |
| `answer_card` 向量 | 112，1024 维 |
| `knowledge_point` 向量 | 74，1024 维 |

## 4. 向量生成

当前 seed SQL 只导入 `embedding_text`，真实向量由本地 Ollama embedding 命令生成。当前已切换为 `bge-m3`，输出 1024 维向量：

```powershell
$env:PYTHONPATH='D:\knowledgebase\src'
py -m kb_rag.cli embed --model bge-m3 --batch-size 8
```

输出文件：

```text
D:\knowledgebase\output\ch01_rag_engine\embeddings\ch01_embedding_vectors.jsonl
D:\knowledgebase\output\ch01_rag_engine\db_load\ch01_embedding_updates.sql
```

导入数据库：

```powershell
psql -h 127.0.0.1 -p 55432 -U postgres -d road_kb -f D:\knowledgebase\output\ch01_rag_engine\db_load\ch01_embedding_updates.sql
```

如果后续切换为其他 embedding 模型，只需更换模型名重新运行，并重新导入更新 SQL。

底层更新语句形式：

```sql
UPDATE embedding_corpus
SET embedding = :vector
WHERE embedding_id = :embedding_id;
```

当前 schema 已按 `bge-m3` 固定为 `vector(1024)`，并创建 HNSW 索引：

```sql
CREATE INDEX IF NOT EXISTS idx_embedding_corpus_hnsw
  ON embedding_corpus USING hnsw (embedding vector_cosine_ops);
```

## 5. 数据库检索验证

CLI：

```powershell
$env:PYTHONPATH='D:\knowledgebase\src'
py -m kb_rag.cli db-summary
py -m kb_rag.cli db-vector-search "数字孪生为什么强调虚实闭环？"
py -m kb_rag.cli db-hybrid-ask "数字孪生为什么强调虚实闭环？"
```

API：

```powershell
$env:PYTHONPATH='D:\knowledgebase\src'
py -m kb_rag.api --port 8767 --database-url 'postgresql://postgres@127.0.0.1:55432/road_kb'
Invoke-RestMethod 'http://127.0.0.1:8767/ask?q=数字孪生为什么强调虚实闭环？&use_db=true'
```

当前验证结果：

| 查询 | 命中 |
|---|---|
| `db-summary` | `answer_cards=112`，`embedding_corpus=186`，`embedded_vectors=186` |
| `db-vector-search` | Top1 `ans_ch01_013`，similarity `0.5977` |
| `db-hybrid-ask` | Top1 `ans_ch01_013` |
| API `use_db=true` | `retriever=postgres_pgvector_hybrid` |

## 6. 检索原则

检索顺序必须保持：

```text
Answer_Cards -> Knowledge_Points -> Concept_Comparison -> Exercises -> Source_Chunks -> Resources
```

其中：

- `answer_cards` 是主回答来源。
- `source_chunks` 只用于证据追溯，不直接输出长段原文。
- `rag_config.fallback_only = true` 的对象不能进入主回答。
- `resources` 只做学习资源推荐。

## 7. 评测结果入库

可将 QA_Evaluation_Testset 的运行结果写入 `rag_eval_runs` 和 `rag_eval_cases`：

```powershell
$env:PYTHONPATH='D:\knowledgebase\src'
py -m kb_rag.cli db-evaluate --retriever keyword
py -m kb_rag.cli db-evaluate --retriever db-hybrid
py -m kb_rag.cli db-eval-runs
```

当前已验证：

| 检索器 | 测试题 | Top1 | Top3 | 通过率 |
|---|---:|---:|---:|---:|
| `keyword` | 443 | 100.00% | 100.00% | 100.00% |
| `db-hybrid` | 443 | 100.00% | 100.00% | 100.00% |

失败样例查询模板：

```text
D:\knowledgebase\src\db\queries\eval_run_summary.sql
D:\knowledgebase\src\db\queries\eval_failures.sql
```

如 embedding 重建过程中被中断，不必整章重跑。可只重算受影响的 `Embedding_Corpus` 记录，再刷新 `ch01_embedding_vectors.jsonl` 和 `ch01_embedding_updates.sql` 后导入数据库。
