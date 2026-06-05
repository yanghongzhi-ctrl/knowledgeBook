# 第10、11章 Source_Chunks 人工复核交接包

说明：本交接包汇总全量非正式 proposed 草案。它不是正式审批文件，不能直接触发 normalize/release 的人工确认逻辑。

- source proposed: `D:\knowledgebase\data\review\ch10_ch11_full_source_boundary_manual_approvals.proposed.json`
- validation_ok: `True`
- validation_errors: `0`
- validation_warnings: `0`
- formal_file_exists: `False`
- total review items: `51`
- formal_ready_without_human_review: `False`

## Decision Counts

| decision | count |
|---|---:|
| `confirm_boundary_fragment` | 7 |
| `confirm_candidate_anchor` | 5 |
| `confirm_teaching_summary` | 9 |
| `manual_anchor_pending` | 30 |

## Risk Counts

| risk | count |
|---|---:|
| `high` | 30 |
| `low` | 5 |
| `medium` | 16 |

## Priority Counts

| priority | count |
|---|---:|
| `P1_ch10_formula_gap` | 1 |
| `P1_ch10_quick_confirm` | 4 |
| `P2_ch10_boundary_summary` | 8 |
| `P2_ch11_quick_confirm` | 1 |
| `P3_ch11_application_scene_manual` | 29 |
| `P4_ch11_boundary_summary` | 8 |

## Scene Counts

| scene | count |
|---|---:|
| 全生命周期资产管理与价值评估 | 3 |
| 基于数字主线的数字化交付 | 4 |
| 数字化设计与多物理场仿真 | 9 |
| 智慧交通治理与韧性服务 | 1 |
| 智能化施工与质量闭环控制 | 5 |
| 预测性养护与结构健康监测 | 7 |

## Human Review Guidance

- `confirm_candidate_anchor`：概念对应候选，不等同于教材逐字引用。 确认 Source_Chunk 与候选段落表达同一概念，且段落范围准确。
- `confirm_boundary_fragment`：候选文本属于公式、列表或跨段边界片段。 确认是否可保留为片段；若缺公式变量或上下文，应改为 split_required 或 manual_anchor_pending。
- `confirm_teaching_summary`：教材中有术语或主题支撑，但 Source_Chunk 是教学化摘要。 确认术语锚点足够支撑摘要，不把该条标为逐字原文。
- `manual_anchor_pending`：仍需人工补更精确教材锚点或维持待定。 回看 Word 原文，补 paragraph span、改 decision，或保留待定并写清原因。

## Remaining Human Actions

- 逐条审定 51 条 proposed decision，尤其是 30 条 manual_anchor_pending。
- 确认 confirm_teaching_summary 只作为教学摘要证据，不标注为教材逐字引用。
- 确认 confirm_boundary_fragment 是否需要拆分、补上下文或保留边界片段。
- 人工确认后，另存为 ch10_ch11_source_boundary_manual_approvals.json 并复跑 normalize/release。

## Packet Inputs

| packet | exists | summary |
|---|---|---|
| `D:\knowledgebase\output\ch10_p1_source_review_packet_2026-06-05.json` | `True` | `{"total": 5, "quick_confirm": 4, "formula_gap": 1}` |
| `D:\knowledgebase\output\ch10_p2_source_review_packet_2026-06-05.json` | `True` | `{"total": 8, "filled": 0, "open": 8, "by_review_status": {"boundary_fragment_review": 5, "term_supported_summary_review": 3}, "by_suggested_decision": {"confirm_boundary_fragment": 5, "confirm_teaching_summary": 3}}` |
| `D:\knowledgebase\output\ch11_p2_quick_source_review_packet_2026-06-05.json` | `True` | `{"total": 1, "filled": 0, "open": 1, "by_review_status": {"candidate_anchor_review": 1}, "by_suggested_decision": {"confirm_candidate_anchor": 1}}` |
| `D:\knowledgebase\output\ch11_application_scene_review_packet_2026-06-05.json` | `True` | `{"total": 29, "open": 29, "filled": 0, "by_scene": {"asset_management": 3, "construction_control": 5, "design_multiphysics": 9, "digital_delivery": 4, "predictive_maintenance": 7, "traffic_governance": 1}, "by_decision": {"": 29}, "group_count": 6}` |
| `D:\knowledgebase\output\ch11_p4_source_review_packet_2026-06-05.json` | `True` | `{"total": 8, "filled": 0, "open": 8, "by_review_status": {"boundary_fragment_review": 2, "term_supported_summary_review": 6}, "by_suggested_decision": {"confirm_boundary_fragment": 2, "confirm_teaching_summary": 6}}` |
