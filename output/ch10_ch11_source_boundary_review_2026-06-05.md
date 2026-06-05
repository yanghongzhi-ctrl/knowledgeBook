# 第10、11章 Source_Chunks 证据边界复核包

说明：本报告只生成候选教材段落和复核动作，不把候选结果标记为人工确认，也不把教学摘要伪装成逐字原文。

## 总览

- 总计：51
- 按复核状态：`{'boundary_fragment_review': 7, 'candidate_anchor_review': 5, 'manual_anchor_required': 30, 'term_supported_summary_review': 9}`
- 按原始分级：`{'cross_paragraph_or_formula_fragment': 7, 'needs_manual_textbook_anchor': 35, 'summary_with_term_support': 9}`

## ch10

- 统计：`{'total': 13, 'by_review_status': {'boundary_fragment_review': 5, 'candidate_anchor_review': 4, 'manual_anchor_required': 1, 'term_supported_summary_review': 3}, 'by_original_classification': {'cross_paragraph_or_formula_fragment': 5, 'needs_manual_textbook_anchor': 5, 'summary_with_term_support': 3}}`

| Chunk | 原分级 | 复核状态 | 候选段 | 分数 | 动作 |
|---|---|---|---:|---:|---|
| `ch10_src_002` | summary_with_term_support | term_supported_summary_review | 4781-4781 | 0.518 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch10_src_018` | cross_paragraph_or_formula_fragment | boundary_fragment_review | 4815-4815 | 0.871 | 疑似跨段、公式或列表边界片段；人工确认是否拆分、补公式上下文或仅保留为摘要。 |
| `ch10_src_031` | summary_with_term_support | term_supported_summary_review | 4912-4912 | 0.885 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch10_src_034` | cross_paragraph_or_formula_fragment | boundary_fragment_review | 4926-4926 | 0.716 | 疑似跨段、公式或列表边界片段；人工确认是否拆分、补公式上下文或仅保留为摘要。 |
| `ch10_src_060` | cross_paragraph_or_formula_fragment | boundary_fragment_review | 5024-5026 | 0.963 | 疑似跨段、公式或列表边界片段；人工确认是否拆分、补公式上下文或仅保留为摘要。 |
| `ch10_src_075` | cross_paragraph_or_formula_fragment | boundary_fragment_review | 5081-5083 | 0.896 | 疑似跨段、公式或列表边界片段；人工确认是否拆分、补公式上下文或仅保留为摘要。 |
| `ch10_src_087` | cross_paragraph_or_formula_fragment | boundary_fragment_review | 5133-5133 | 0.920 | 疑似跨段、公式或列表边界片段；人工确认是否拆分、补公式上下文或仅保留为摘要。 |
| `ch10_src_096` | summary_with_term_support | term_supported_summary_review | 4794-4794 | 0.853 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch10_src_135` | needs_manual_textbook_anchor | candidate_anchor_review | 4884-4884 | 0.839 | 已生成候选 Word 段落；人工确认后可作为概念依据对应，不标记为逐字原文。 |
| `ch10_src_140` | needs_manual_textbook_anchor | manual_anchor_required | 4913-4913 | 0.263 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch10_src_144` | needs_manual_textbook_anchor | candidate_anchor_review | 4920-4920 | 0.910 | 已生成候选 Word 段落；人工确认后可作为概念依据对应，不标记为逐字原文。 |
| `ch10_src_146` | needs_manual_textbook_anchor | candidate_anchor_review | 4922-4922 | 0.782 | 已生成候选 Word 段落；人工确认后可作为概念依据对应，不标记为逐字原文。 |
| `ch10_src_148` | needs_manual_textbook_anchor | candidate_anchor_review | 4927-4927 | 0.919 | 已生成候选 Word 段落；人工确认后可作为概念依据对应，不标记为逐字原文。 |

## ch11

- 统计：`{'total': 38, 'by_review_status': {'boundary_fragment_review': 2, 'candidate_anchor_review': 1, 'manual_anchor_required': 29, 'term_supported_summary_review': 6}, 'by_original_classification': {'cross_paragraph_or_formula_fragment': 2, 'needs_manual_textbook_anchor': 30, 'summary_with_term_support': 6}}`

| Chunk | 原分级 | 复核状态 | 候选段 | 分数 | 动作 |
|---|---|---|---:|---:|---|
| `ch11_src_046` | needs_manual_textbook_anchor | candidate_anchor_review | 5362-5364 | 0.887 | 已生成候选 Word 段落；人工确认后可作为概念依据对应，不标记为逐字原文。 |
| `ch11_src_117` | needs_manual_textbook_anchor | manual_anchor_required | 5568-5568 | 0.422 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_118` | summary_with_term_support | term_supported_summary_review | 5568-5568 | 0.218 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch11_src_119` | needs_manual_textbook_anchor | manual_anchor_required | 5556-5557 | 0.148 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_120` | summary_with_term_support | term_supported_summary_review | 5557-5558 | 0.168 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch11_src_121` | needs_manual_textbook_anchor | manual_anchor_required | 5557-5559 | 0.165 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_122` | needs_manual_textbook_anchor | manual_anchor_required | 5556-5557 | 0.156 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_123` | cross_paragraph_or_formula_fragment | boundary_fragment_review | 5555-5557 | 0.208 | 疑似跨段、公式或列表边界片段；人工确认是否拆分、补公式上下文或仅保留为摘要。 |
| `ch11_src_124` | needs_manual_textbook_anchor | manual_anchor_required | 5557-5557 | 0.174 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_125` | needs_manual_textbook_anchor | manual_anchor_required | 5556-5557 | 0.162 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_126` | needs_manual_textbook_anchor | manual_anchor_required | 5555-5557 | 0.174 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_127` | needs_manual_textbook_anchor | manual_anchor_required | 5556-5557 | 0.146 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_128` | needs_manual_textbook_anchor | manual_anchor_required | 5557-5557 | 0.175 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_130` | summary_with_term_support | term_supported_summary_review | 5572-5573 | 0.424 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch11_src_134` | needs_manual_textbook_anchor | manual_anchor_required | 5575-5576 | 0.233 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_135` | needs_manual_textbook_anchor | manual_anchor_required | 5577-5578 | 0.336 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_136` | needs_manual_textbook_anchor | manual_anchor_required | 5557-5558 | 0.161 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_137` | needs_manual_textbook_anchor | manual_anchor_required | 5557-5558 | 0.167 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_138` | summary_with_term_support | term_supported_summary_review | 5579-5579 | 0.323 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch11_src_139` | needs_manual_textbook_anchor | manual_anchor_required | 5579-5581 | 0.282 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_140` | needs_manual_textbook_anchor | manual_anchor_required | 5557-5559 | 0.236 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_142` | needs_manual_textbook_anchor | manual_anchor_required | 5583-5583 | 0.223 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_143` | needs_manual_textbook_anchor | manual_anchor_required | 5583-5583 | 0.247 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_144` | needs_manual_textbook_anchor | manual_anchor_required | 5584-5585 | 0.339 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_145` | needs_manual_textbook_anchor | manual_anchor_required | 5586-5587 | 0.278 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_146` | needs_manual_textbook_anchor | manual_anchor_required | 5588-5588 | 0.254 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_147` | needs_manual_textbook_anchor | manual_anchor_required | 5354-5355 | 0.206 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_148` | needs_manual_textbook_anchor | manual_anchor_required | 5589-5589 | 0.164 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_149` | summary_with_term_support | term_supported_summary_review | 5589-5590 | 0.270 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch11_src_150` | needs_manual_textbook_anchor | manual_anchor_required | 5592-5592 | 0.181 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_151` | needs_manual_textbook_anchor | manual_anchor_required | 5592-5592 | 0.229 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_152` | needs_manual_textbook_anchor | manual_anchor_required | 5555-5557 | 0.216 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_154` | cross_paragraph_or_formula_fragment | boundary_fragment_review | 5594-5595 | 0.411 | 疑似跨段、公式或列表边界片段；人工确认是否拆分、补公式上下文或仅保留为摘要。 |
| `ch11_src_155` | needs_manual_textbook_anchor | manual_anchor_required | 5557-5558 | 0.179 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_156` | needs_manual_textbook_anchor | manual_anchor_required | 5596-5597 | 0.297 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_157` | summary_with_term_support | term_supported_summary_review | 5557-5558 | 0.203 | 保留为教学摘要候选；人工确认术语锚点是否足以支撑该 Source_Chunk。 |
| `ch11_src_158` | needs_manual_textbook_anchor | manual_anchor_required | 5597-5599 | 0.265 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
| `ch11_src_160` | needs_manual_textbook_anchor | manual_anchor_required | 5603-5604 | 0.258 | 未形成稳定候选段落；需人工回看教材原文，决定补锚点、改写边界或降级为教学摘要。 |
