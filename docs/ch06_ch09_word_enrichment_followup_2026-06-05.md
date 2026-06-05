# 第6、9章 Word 证据分级补强记录

日期：2026-06-05

## 目标

延续第7、8章实践章节的处理方式，将第6、9章 Word alignment 审计结果写回 raw 包与发布包，形成可复跑的教材证据分级字段。该流程不作为人工审批流程，只作为教材型知识库的自动质量维护信号。

## 脚本调整

- `scripts/normalize_ch06.py` 新增 `--word-alignment` 参数。
- 第6章归一化流程复用 `scripts/normalize_operation_chapters.py` 中的 `apply_word_alignment_enrichment`。
- 修复第6章从 raw 目录原地重建时 jsonl 源文件与目标文件相同导致的复制失败。
- 第6章 `metadata` 改为保留已有维护字段，避免覆盖 `metadata.word_alignment`。

## 自动证据分级结果

| 章节 | Source_Chunks enriched | high | medium | low | Answer_Cards enriched | 直接命中 | 教学化改写支持 | 概念比较支持 | 直接问题未命中 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ch06 | 150 | 94 | 32 | 24 | 180 | 94 | 86 | 0 | 0 |
| ch09 | 150 | 119 | 29 | 2 | 256 | 2 | 203 | 15 | 36 |

说明：

- `high` 表示 Source_Chunks 与 Word 正文或标题存在直接支撑，但仍标记为非逐字引用。
- `medium` 表示局部文本、概念或操作主题可支撑，适合作为答案核验依据。
- `low` 表示结构化教学摘要不宜当作教材原句输出，只用于任务/知识点检索辅助。
- ch09 的 36 条“直接问题未命中”主要集中在地质风险选线后半段操作卡、故障排查卡和少量跨软件概念卡；它们保留为教学化问题入口，不作为人工审批阻塞项。

## 发布验证

ch06 full release：

- validate：errors=0，warnings=0
- local QA：180/180
- resource evaluation：3/3
- embeddings：261/261
- DB keyword：180/180
- DB hybrid：30/30

ch09 full release：

- validate：errors=0，warnings=0
- local QA：256/256
- resource evaluation：12/12
- embeddings：384/384
- DB keyword：256/256
- DB hybrid：30/30

平台回归：

- 前端/API 烟测：74 checks，failures=0
- 自动章节路由：27346 checks，failures=0
- 前端题库已刷新：ch06 225 条，ch09 276 条

API 抽测：

- “AutoCAD如何新建图层？” -> ch06 / `ans_ch06_task_018_howto`
- “BIM+GIS集成层次包含哪些？” -> ch09 / `ans_ch09_237`

## 后续自动关注点

- 将 ch09 的 36 条低置信答案卡继续归入“教学化入口”质量桶，后续可通过教材正文或互动脚本再补强问法锚点。
- 实践章节 ch06-ch09 已形成统一的 Word 证据分级字段，可在后续质量仪表盘中按 `evidence_quality_profile.evidence_confidence` 和 `word_alignment.support_type` 统计。
