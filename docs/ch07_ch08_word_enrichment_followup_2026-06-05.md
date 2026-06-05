# 第7、8章 Word 证据分级补强记录（2026-06-05）

本轮延续第10、11章的纠偏口径：第7、8章属于教材定版型操作知识库，不再把 Word 对照缺口解释为等待人工审批，而是转化为可复跑的自动证据质量分级与维护字段。补强只写入证据边界、问法定版和检索维护信息，不新增教材未支持的知识结论。

## 规范化脚本

| 项目 | 结果 |
|---|---|
| 脚本 | `scripts/normalize_operation_chapters.py` |
| 新增输入 | `--word-alignment output/word_alignment_ch06_ch09_2026-06-04.json` |
| Source_Chunks | 写入 `word_alignment`、`word_correspondence`、`evidence_quality_profile`、`word_verification` |
| Answer_Cards | 写入 `word_alignment.support_type`，区分直接命中、任务/知识点支撑、概念比较支撑 |
| ch08重复问法 | 重复规范问题自动定版为“场景:问题”，原短问法保留为 `student_question_patterns` |

## 自动分级结果

| 章节 | Source_Chunks补强 | medium | low | Answer_Cards补强 | 答案卡低置信 |
|---|---:|---:|---:|---:|---:|
| ch07 | 150 | 60 | 90 | 265 | 0 |
| ch08 | 160 | 68 | 92 | 262 | 0 |

ch07 答案卡 265 条均为 `direct_word_question_hit`。  
ch08 答案卡中，6 条为 `direct_word_question_hit`，252 条为 `teaching_rewrite_supported_by_task_or_kp`，4 条为 `teaching_rewrite_supported_by_concept_comparison`。

## 发布验证

| 章节 | validate | QA | 资源评测 | embedding | DB keyword | DB hybrid | 状态 |
|---|---|---:|---:|---:|---:|---:|---|
| ch07 | errors=0, warnings=0 | 265/265 | 2/2 | 466/466 | 265/265 | 30/30 | released |
| ch08 | errors=0, warnings=0 | 262/262 | 4/4 | 478/478 | 262/262 | 30/30 | released |

平台回归：

| 检查项 | 结果 |
|---|---|
| 前端/API烟测 | ch01-ch11 共 74 项，失败 0 |
| 自动章节路由 | 27,346 次检查，失败 0 |
| 前端题库 | 已重建，ch07=376，ch08=296 |

## 抽测

| 问题 | 命中 |
|---|---|
| 纬地如何新建纬地项目？ | `ans_ch07_001` |
| PDF输出比例不对怎么办？ | `ans_ch08_0186`，通过场景化规范问题进入具体操作排查 |
| ORD参数化架构是什么？ | `ans_ch08_0001` |

## 后续口径

第7、8章的 `Source_Chunks` 大量属于操作型结构化摘要，不应强行标成教材原句命中。当前处理方式是：答案卡、知识点和操作任务作为主检索/主回答对象；`Source_Chunks` 作为教材证据层和维护审计层，不直接整段输出给学生。后续若补入正式操作视频或截图，只需要继续更新媒体资源表和发布包，不需要回到人工审批流程。
