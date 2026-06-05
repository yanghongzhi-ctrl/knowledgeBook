# ch08 知识库发布报告

- 版本：`ch08_kb_v1.0`
- 状态：`released`
- 知识包：`D:\knowledgebase\data\raw\ch08\第8章_道路BIM软件的使用_知识库_v1.0操作完备版.json`
- 开始时间：2026-06-04T15:32:07
- 完成时间：2026-06-04T15:39:00

## 发布步骤

| 步骤 | 状态 | 摘要 |
|---|---|---|
| validate | passed | errors=0, warnings=13 |
| quality | passed | ambiguous_qa=0, duplicate_canonical=13 |
| export | passed | exported_files=25 |
| sql_export | passed | seed_sql_bytes=4908233 |
| local_qa_evaluation | passed | passed=262/262 (100.00%) |
| local_resource_evaluation | passed | passed=4/4 (100.00%) |
| embeddings | passed | generated=478/478, dimensions=[1024] |
| db_import | passed | counts_ok=True, embedded_vectors=478 |
| db_keyword_evaluation | passed | passed=262/262 (100.00%) |
| db_hybrid_evaluation | passed | passed=30/30 (100.00%) |
| mark_released | passed | version_id=ch08_kb_v1.0 |

## 校验问题

- 警告：Answer cards have duplicate canonical question 'pdf输出比例不对怎么办': ans_ch08_0186, ans_ch08_0187, ans_ch08_0189, ans_ch08_0193, ans_ch08_0202, ans_ch08_0223, ans_ch08_0231, ans_ch08_0248, ans_ch08_0252
- 警告：Answer cards have duplicate canonical question '加宽未应用怎么办': ans_ch08_0184, ans_ch08_0196, ans_ch08_0242, ans_ch08_0257
- 警告：Answer cards have duplicate canonical question '命名边界出图缺失怎么办': ans_ch08_0192, ans_ch08_0205, ans_ch08_0224, ans_ch08_0225, ans_ch08_0230, ans_ch08_0233, ans_ch08_0238, ans_ch08_0243, ans_ch08_0246, ans_ch08_0254, ans_ch08_0259
- 警告：Answer cards have duplicate canonical question '工程量统计不完整怎么办': ans_ch08_0173, ans_ch08_0183, ans_ch08_0209, ans_ch08_0216, ans_ch08_0236, ans_ch08_0253, ans_ch08_0261
- 警告：Answer cards have duplicate canonical question '平面线形修改后未联动怎么办': ans_ch08_0182, ans_ch08_0206, ans_ch08_0218
- 警告：Answer cards have duplicate canonical question '廊道模型是什么': ans_ch08_0009, ans_ch08_0034
- 警告：Answer cards have duplicate canonical question '廊道没有生成怎么办': ans_ch08_0191, ans_ch08_0194, ans_ch08_0200, ans_ch08_0210, ans_ch08_0214, ans_ch08_0228, ans_ch08_0232, ans_ch08_0256
- 警告：Answer cards have duplicate canonical question '模型不显示怎么办': ans_ch08_0180, ans_ch08_0181, ans_ch08_0185, ans_ch08_0198, ans_ch08_0204, ans_ch08_0219, ans_ch08_0258
- 警告：Answer cards have duplicate canonical question '模板结构变形异常怎么办': ans_ch08_0174, ans_ch08_0177, ans_ch08_0190, ans_ch08_0212, ans_ch08_0221, ans_ch08_0229, ans_ch08_0249
- 警告：Answer cards have duplicate canonical question '纵断面图标注缺失怎么办': ans_ch08_0178, ans_ch08_0207, ans_ch08_0226, ans_ch08_0234, ans_ch08_0237, ans_ch08_0244, ans_ch08_0251, ans_ch08_0255
- 警告：Answer cards have duplicate canonical question '纵断面地面线不更新怎么办': ans_ch08_0176, ans_ch08_0188, ans_ch08_0201, ans_ch08_0203, ans_ch08_0208, ans_ch08_0215, ans_ch08_0240, ans_ch08_0241, ans_ch08_0262
- 警告：Answer cards have duplicate canonical question '超高横坡不正确怎么办': ans_ch08_0195, ans_ch08_0199, ans_ch08_0213, ans_ch08_0217, ans_ch08_0220, ans_ch08_0227
- 警告：Answer cards have duplicate canonical question '边坡不能连接地形怎么办': ans_ch08_0175, ans_ch08_0179, ans_ch08_0197, ans_ch08_0211, ans_ch08_0222, ans_ch08_0235, ans_ch08_0239, ans_ch08_0245, ans_ch08_0247, ans_ch08_0250, ans_ch08_0260

## 结论

本版本已通过发布门槛并标记为 released。

JSON 详情：`D:\knowledgebase\output\ch08_rag_engine\reports\release_report_ch08.json`
