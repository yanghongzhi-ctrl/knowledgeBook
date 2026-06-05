# 第10、11章 Word 补强复跑记录（2026-06-05）

本轮继续优化第10、11章 Word 补强流程，重点解决规范化脚本每次从用户上传原始 JSON 重建 raw 包时，差量标题补强可能丢失的问题。候选生成脚本现在默认读取初始 Word 审计基线 `output/word_alignment_ch10_ch11_2026-06-04.json`，输出累计补强包；规范化脚本每次复跑均可完整恢复标题别名、问法别名和证据边界维护字段。

## 本轮改动

| 项目 | 结果 |
|---|---|
| 章节结构映射 | `scripts/build_ch10_ch11_word_enrichment.py` 新增 `Chapter_Structure` 作为标题别名目标 |
| 标题等价评分 | 新增标题序号剥离、图题噪声压缩、中文二字片段重合评分 |
| 累计补强包 | ch10 初始 18 个标题缺口全部自动补强；ch11 初始 2 个标题缺口保留自动补强 |
| 人工复核清单 | 新增 `output/ch10_ch11_word_manual_review_2026-06-05.json` 与 `.csv`，标题类复核 0 条，Source_Chunks 证据边界复核 51 条 |

## Word 复核

| 章节 | 标题覆盖 | 知识点覆盖 | 答案卡直接命中 | Source_Chunks |
|---|---:|---:|---:|---|
| ch10 | 32/32 | 98/98 | 168/308 | exact 125 / partial 21 / concept 1 / missing 13 |
| ch11 | 16/16 | 78/78 | 288/295 | exact 96 / partial 20 / concept 6 / missing 38 |

## 发布与回归

| 检查项 | 结果 |
|---|---|
| ch10 full release | released；validate errors=0；QA 301/301；资源 4/4；embedding 450/450；DB keyword 301/301；DB hybrid 30/30 |
| ch11 full release | released；validate errors=0；QA 295/295；资源 5/5；embedding 373/373；DB keyword 295/295；DB hybrid 30/30 |
| 前端题库 | `web/question-bank.json` 已重建，ch10 338 条，ch11 315 条 |
| 平台烟测 | ch01-ch11 共 74 项检查，失败 0 |
| 自动章节路由 | 49,753 次检查，失败 0 |
| 专项问答 | ch10“三大范式”命中 `ans_ch10_001`；ch11“道路数字孪生是什么”命中 `ans_ch11_001` |
| 残片检查 | 未发现 Word XML 残片、`实现动。` 或 `转型。。` |

## 仍需人工复核

1. ch10：`summary_with_term_support` 3 条、`cross_paragraph_or_formula_fragment` 5 条、`needs_manual_textbook_anchor` 5 条。
2. ch11：`summary_with_term_support` 6 条、`cross_paragraph_or_formula_fragment` 2 条、`needs_manual_textbook_anchor` 30 条。
3. 上述 51 条已进入 `output/ch10_ch11_word_manual_review_2026-06-05.csv`，下一轮可按该表逐条回看 Word 原文，决定保留为教学摘要、拆分证据片段，或补充更精确教材锚点。

## Source_Chunks 证据边界复核包

已新增 `scripts/review_ch10_ch11_source_boundaries.py`，读取人工复核清单、教材 Word 正文与当前 raw 包，为 51 条待复核 Source_Chunks 生成候选 Word 段落、复核状态和动作建议。该脚本只生成候选，不把候选段落标记为人工确认，也不把教学摘要标记为逐字原文。

输出文件：

| 文件 | 用途 |
|---|---|
| `output/ch10_ch11_source_boundary_review_2026-06-05.json` | 结构化复核包，可被规范化脚本回写 |
| `output/ch10_ch11_source_boundary_review_2026-06-05.csv` | 面向人工复核的表格 |
| `output/ch10_ch11_source_boundary_review_2026-06-05.md` | 分章摘要报告 |

复核分级结果：

| 复核状态 | 数量 | 含义 |
|---|---:|---|
| `term_supported_summary_review` | 9 | 有术语支撑，建议保留为教学摘要候选，仍需人工确认术语锚点是否充分 |
| `boundary_fragment_review` | 7 | 疑似跨段、公式或列表边界，需人工决定是否拆分或补上下文 |
| `candidate_anchor_review` | 5 | 已生成较稳定候选 Word 段落，可供人工确认概念依据 |
| `manual_anchor_required` | 30 | 未形成稳定候选段落，仍需人工回看教材 |

规范化回写：

| 章节 | 回写 Source_Chunks | 状态分布 |
|---|---:|---|
| ch10 | 13 | boundary 5 / candidate 4 / manual 1 / term-summary 3 |
| ch11 | 38 | boundary 2 / candidate 1 / manual 29 / term-summary 6 |

发布与回归：

| 检查项 | 结果 |
|---|---|
| ch10 full release | released；validate errors=0；warnings=0；QA 301/301；资源 4/4；DB keyword 301/301；DB hybrid 30/30 |
| ch11 full release | released；validate errors=0；warnings=0；QA 295/295；资源 5/5；DB keyword 295/295；DB hybrid 30/30 |
| 前端/API 烟测 | ch01-ch11 共 74 项检查，失败 0 |
| 自动章节路由 | 49,753 次检查，失败 0 |
| 专项问答 | ch10/ch11 关键问题均命中原答案卡，且未出现坏文本残片 |

后续人工复核应优先处理：

1. ch10 的 `candidate_anchor_review` 4 条，可最快确认并固化教材锚点。
2. ch10 的 `manual_anchor_required` 1 条，即 `ch10_src_140`，疑似公式变量残缺。
3. ch11 的 `manual_anchor_required` 29 条，多集中于典型应用场景扩展段，建议按应用场景逐组判断是否保留为教学摘要。

## 人工审批模板与复核优先级

本轮新增 `scripts/build_ch10_ch11_source_review_approval_template.py`，将上一轮 51 条 Source_Chunks 证据边界复核结果转换为可填写的人工审批模板、优先级 CSV 与复核 dossier。该模板不会自动生效；需要复制为正式审批文件后，由规范化脚本读取并回写人工决策。

输出文件：

| 文件 | 用途 |
|---|---|
| `data/review/ch10_ch11_source_boundary_manual_approvals.template.json` | 人工审批模板，默认 decision 为空 |
| `output/ch10_ch11_source_boundary_review_priority_2026-06-05.csv` | 按优先级排序的复核表 |
| `output/ch10_ch11_source_boundary_review_dossier_2026-06-05.md` | 含 Source_Chunk 与候选 Word 段落的复核 dossier |

优先级分组：

| 优先级 | 数量 | 处理建议 |
|---|---:|---|
| `P1_ch10_quick_confirm` | 4 | 第10章候选锚点较稳定，优先人工确认 |
| `P1_ch10_formula_gap` | 1 | 第10章公式/变量残缺，优先回看原文 |
| `P2_ch10_boundary_summary` | 8 | 第10章边界/摘要类复核 |
| `P2_ch11_quick_confirm` | 1 | 第11章候选锚点较稳定，可快速确认 |
| `P3_ch11_application_scene_manual` | 29 | 第11章典型应用场景扩展段，建议按场景成组复核 |
| `P4_ch11_boundary_summary` | 8 | 第11章边界/摘要类复核 |

规范化脚本新增 `--manual-approvals` 参数，默认读取 `data/review/ch10_ch11_source_boundary_manual_approvals.json`。当前该正式审批文件尚不存在，因此本轮规范化确认 `manual_approvals_applied=0`，不会误把候选项标记为人工确认。

发布与回归：

| 检查项 | 结果 |
|---|---|
| ch10 full release | released；validate errors=0；warnings=0；QA 301/301；资源 4/4；DB keyword 301/301；DB hybrid 30/30 |
| ch11 full release | released；validate errors=0；warnings=0；QA 295/295；资源 5/5；DB keyword 295/295；DB hybrid 30/30 |
| 前端/API 烟测 | ch01-ch11 共 74 项检查，失败 0 |
| 自动章节路由 | 49,753 次检查，失败 0 |
| 关键问答 | ch10/ch11 关键问题均命中原答案卡，且无坏文本残片 |

## 复核工作台与审批校验

本轮继续把 Source_Chunks 人工复核流程产品化，新增静态复核工作台和审批文件校验脚本，便于后续逐条确认 51 条证据边界。

新增文件：

| 文件 | 用途 |
|---|---|
| `web/source-review.html` | 本地复核工作台页面 |
| `web/source-review.css` | 复核工作台样式 |
| `web/source-review.js` | 筛选、填写 decision、导出审批 JSON |
| `web/source-review-data.json` | 由审批模板脚本生成的页面数据 |
| `scripts/validate_ch10_ch11_source_manual_approvals.py` | 校验正式审批 JSON 的 chunk、decision、段落范围和异常决策 |

访问地址：

`http://127.0.0.1:5174/web/source-review.html`

工作台能力：

| 功能 | 说明 |
|---|---|
| 优先级筛选 | 可按 P1/P2/P3/P4 分组查看 |
| 决策筛选 | 可按建议决策筛选，如候选锚点、教学摘要、边界片段 |
| 对照查看 | 左侧显示 Source_Chunk，右侧显示候选 Word 段落 |
| 决策填写 | 可填写 `decision` 与 `reviewer_notes` |
| JSON 导出 | 导出结构与 `--manual-approvals` 兼容的审批 JSON |

校验结果：

| 检查项 | 结果 |
|---|---|
| 缺失正式审批文件 | `--allow-missing` 通过，仅提示不会应用人工决策 |
| 模板审批文件 | 51 条全部为空 decision，校验通过 |
| 浏览器页面检查 | 51 条加载正常；默认选中 `ch10_src_135`；Source_Chunk、候选段落、导出按钮均存在 |

后续使用方式：

1. 在复核工作台填写若干条 decision 并导出 JSON。
2. 将导出的 JSON 作为正式审批文件 `data/review/ch10_ch11_source_boundary_manual_approvals.json`。
3. 运行 `scripts/validate_ch10_ch11_source_manual_approvals.py` 校验。
4. 校验通过后运行 `scripts/normalize_ch10_ch11.py --chapters ch10 ch11`，人工确认结果会写回 raw 包。

## P1 复核辅助与工作台增强

本轮继续围绕第10章 P1 项做研发增强，目标是让“快速确认”和“公式缺口”有更集中的上下文材料，同时让复核工作台可以导入/导出正式审批 JSON。

新增文件：

| 文件 | 用途 |
|---|---|
| `scripts/build_ch10_p1_source_review_packet.py` | 生成第10章 P1 专项复核包 |
| `output/ch10_p1_source_review_packet_2026-06-05.json` | P1 结构化复核包 |
| `output/ch10_p1_source_review_packet_2026-06-05.md` | P1 人工查看报告，含候选段落前后文 |

P1 专项包统计：

| 类型 | 数量 |
|---|---:|
| `P1_ch10_quick_confirm` | 4 |
| `P1_ch10_formula_gap` | 1 |

复核工作台增强：

| 功能 | 说明 |
|---|---|
| 导入审批 JSON | 可加载已导出的审批文件并恢复填写状态 |
| 只下载已填写 | 可只导出非空 decision，便于阶段性小批量审批 |
| 页面内校验 | 对非法 decision、确认项缺少段落范围、确认项缺少 reviewer_notes 给出提示 |
| 状态提示 | 显示已填写数量和校验状态 |

验证结果：

| 检查项 | 结果 |
|---|---|
| P1 复核包生成 | 5 条，quick confirm 4 / formula gap 1 |
| 正式审批文件缺失校验 | 通过，仅警告不会应用人工决策 |
| 工作台浏览器验证 | 51 条加载正常；默认选中 `ch10_src_135`；导入按钮、只下载已填写按钮、校验提示均存在 |
| 静态资源 | `source-review-data.json` 可通过本地前端服务访问 |

## P1 自动建议草案与批量填写

本轮新增 P1 自动建议审批草案，文件名明确为 proposed，不会被 `normalize_ch10_ch11.py` 默认读取。该草案只用于辅助人工复核，不能视为人工确认。

新增文件：

| 文件 | 用途 |
|---|---|
| `scripts/build_ch10_p1_proposed_approvals.py` | 生成第10章 P1 proposed 审批草案 |
| `data/review/ch10_p1_source_boundary_manual_approvals.proposed.json` | 非活动审批草案，含 5 条非空建议 |

草案结果：

| decision | 数量 |
|---|---:|
| `confirm_candidate_anchor` | 4 |
| `manual_anchor_pending` | 1 |
| 空 decision | 46 |

校验结果：

`scripts/validate_ch10_ch11_source_manual_approvals.py --approvals data/review/ch10_p1_source_boundary_manual_approvals.proposed.json` 通过，errors=0，warnings=0。

复核工作台同步增强：

| 功能 | 说明 |
|---|---|
| 填入当前建议 | 对当前筛选范围批量写入 suggested_decision 与建议 reviewer_notes |
| 清空当前填写 | 清空当前筛选范围内已填写 decision/notes |
| 缓存版本更新 | `source-review.html` 引用 `source-review.js/css?v=20260605b` |

浏览器验证：

| 检查项 | 结果 |
|---|---|
| 页面条目 | 51 条 |
| 新按钮 | `填入当前建议`、`清空当前填写` 均存在 |
| 默认状态 | 未填写审批决策 |
| 控制台错误 | 0 |

## 审批草稿 API 与工作台落盘

本轮继续把人工复核流程做成可持续研发闭环：在本地 RAG API 中新增 Source_Chunks 审批草稿读写接口，并在复核工作台中增加“加载草稿 / 保存草稿”。页面只保存 draft，正式审批文件仍需显式确认，避免把自动建议草案误作为人工确认。

新增能力：

| 功能 | 说明 |
|---|---|
| `GET /source-review-approvals?target=draft` | 读取草稿审批文件及校验结果 |
| `POST /source-review-approvals?target=draft` | 保存草稿审批文件 |
| `GET /source-review-approvals?target=formal` | 查看正式审批文件是否存在及校验结果 |
| `POST /source-review-approvals?target=formal` | 仅当 JSON 包含 `confirm_write_formal=true` 时允许写入正式审批 |
| 工作台草稿按钮 | `source-review.html` 可直接加载/保存 `data/review/ch10_ch11_source_boundary_manual_approvals.draft.json` |

验证结果：

| 检查项 | 结果 |
|---|---|
| API 编译 | `py -m py_compile src/kb_rag/api.py` 通过 |
| 草稿保存 | 已将 P1 proposed 草案保存为 draft，非空 decision 5 条 |
| 草稿校验 | `scripts/validate_ch10_ch11_source_manual_approvals.py --approvals data/review/ch10_ch11_source_boundary_manual_approvals.draft.json` 通过，errors=0，warnings=0 |
| 正式审批保护 | 未带 `confirm_write_formal=true` 写入 formal 被拒绝 |
| 正式审批文件 | `data/review/ch10_ch11_source_boundary_manual_approvals.json` 仍不存在，规范化脚本不会应用人工决策 |
| 页面资源检查 | `source-review.html`、`source-review.js`、`source-review-data.json` 均可通过本地前端服务读取；页面含 51 条复核数据 |
| 关键问答回归 | ch10 命中 `ans_ch10_001`、ch11 命中 `ans_ch11_001`，均为 high 且各返回 3 个资源推荐 |

当前可用入口：

| 入口 | 地址 |
|---|---|
| 复核工作台 | `http://127.0.0.1:5174/web/source-review.html?fresh=20260605c` |
| 本地 API | `http://127.0.0.1:8768` |

## 审批草稿晋级预检脚本

本轮新增草稿晋级脚本，用于把复核工作台保存的 draft 审批文件转换为可审查的晋级预检报告。脚本默认只 dry-run，不写正式审批文件；只有同时提供 `--write-formal --confirm-reviewed` 时才会把 draft 复制为 formal，并且默认不覆盖已存在 formal 文件。

新增文件：

| 文件 | 用途 |
|---|---|
| `scripts/promote_ch10_ch11_source_review_draft.py` | 校验 draft、生成晋级预检报告、在显式确认时写 formal，并改写正式状态元数据 |
| `output/ch10_ch11_source_boundary_draft_promotion_preview_2026-06-05.json` | 晋级预检结构化报告 |
| `output/ch10_ch11_source_boundary_draft_promotion_preview_2026-06-05.md` | 晋级预检摘要报告 |

当前预检结果：

| 项目 | 结果 |
|---|---:|
| draft 条目 | 51 |
| 已填写 decision | 5 |
| 未填写 decision | 46 |
| ch10 已填写 | 5/13 |
| ch11 已填写 | 0/38 |
| 校验错误 | 0 |
| 校验警告 | 0 |

安全验证：

| 检查项 | 结果 |
|---|---|
| `py -m py_compile` | promote 脚本与 validate 脚本均通过 |
| validate 脚本复用 | `validate_approval_payload` 已抽出，可被 promote 脚本导入 |
| dry-run | 生成预检报告，不写 formal |
| 缺少 `--confirm-reviewed` 的写入测试 | 被拒绝，退出码 1 |
| formal 元数据 | 真正晋级时会写入 `status=manual_review_formal`、`promoted_from`、`promoted_at` |
| 正式审批文件 | `data/review/ch10_ch11_source_boundary_manual_approvals.json` 仍不存在 |

## ch11 应用场景分组复核包

本轮继续推进第11章人工复核材料准备，针对 `P3_ch11_application_scene_manual` 的 29 条待复核 Source_Chunks 新增分组复核包。该脚本只生成辅助材料，不写审批文件；场景归类只依据 Source_Chunk 文本，不使用不稳定候选段落，避免错误候选小标题干扰分组。

新增文件：

| 文件 | 用途 |
|---|---|
| `scripts/build_ch11_application_scene_review_packet.py` | 生成第11章应用场景分组复核包 |
| `output/ch11_application_scene_review_packet_2026-06-05.json` | 结构化分组包，含上下文段落 |
| `output/ch11_application_scene_review_packet_2026-06-05.md` | 人工阅读版复核报告 |
| `output/ch11_application_scene_review_packet_2026-06-05.csv` | 表格版复核清单 |

分组结果：

| 场景组 | 数量 |
|---|---:|
| 数字化设计与多物理场仿真 | 9 |
| 智能化施工与质量闭环控制 | 5 |
| 基于数字主线的数字化交付 | 4 |
| 预测性养护与结构健康监测 | 7 |
| 全生命周期资产管理与价值评估 | 3 |
| 智慧交通治理与韧性服务 | 1 |

验证结果：

| 检查项 | 结果 |
|---|---|
| 脚本编译 | `py -m py_compile scripts/build_ch11_application_scene_review_packet.py` 通过 |
| 包生成 | 29 条 P3 ch11 应用场景复核项全部进入分组包 |
| 场景抽查 | 视距/车辆动力学归入设计仿真；压实/摊铺/预制构件归入施工控制；降阶模型/损伤识别归入预测性养护；车道级数字车流归入交通治理 |

## 复核工作台场景筛选

本轮将第11章应用场景分组包接入 `web/source-review.html`。工作台启动后会尝试读取 `output/ch11_application_scene_review_packet_2026-06-05.json`，并为对应的 29 条 `P3_ch11_application_scene_manual` 条目补充 `scene_id`、`scene_title` 和 `scene_terms`。如果分组包不存在，页面仍按原有方式加载，不影响基础复核。

新增能力：

| 功能 | 说明 |
|---|---|
| 应用场景筛选 | 可按设计仿真、施工控制、数字化交付、预测性养护、资产管理、智慧交通治理筛选 |
| 场景 badge | 条目卡片显示对应应用场景 |
| 详情补充 | 审批详情中显示应用场景和命中词 |
| 关键词检索 | 搜索范围扩展到场景标题 |

验证结果：

| 检查项 | 结果 |
|---|---|
| 静态 HTML | `source-review.html?fresh=20260605d` 含 `sceneFilter` 和新版缓存号 |
| 静态 JS | `source-review.js?v=20260605d` 含场景包加载、筛选和 badge 逻辑 |
| 场景包访问 | `http://127.0.0.1:5174/output/ch11_application_scene_review_packet_2026-06-05.json` 返回 200 |
| 场景索引 | 29 条 ch11 应用场景条目完成索引，`ch11_src_160` 归入“智慧交通治理与韧性服务” |
| JS 初始化 | 在最小 DOM/fetch stub 下动态导入执行通过 |

## 复核工作台场景批处理

本轮继续增强复核工作台，围绕“按场景成组处理 ch11 P3 条目”的工作流增加进度卡和批处理按钮。该功能仍只操作 draft/导出 JSON，不自动写 formal。

新增能力：

| 功能 | 说明 |
|---|---|
| 场景进度卡 | 左侧显示每个应用场景的已填/未填数量和进度条 |
| 场景快速筛选 | 点击场景进度卡即可切换到该场景 |
| 填入当前场景建议 | 仅对当前选中应用场景批量写入 `suggested_decision` 与建议 notes |
| 只下载当前场景 | 导出当前场景对应的审批 JSON 子集，便于分组复核流转 |
| 禁用态保护 | 未选择场景时，场景批处理按钮不可用 |

验证结果：

| 检查项 | 结果 |
|---|---|
| 静态 HTML | `source-review.html?fresh=20260605e` 含 `sceneProgress`、`applySceneSuggested`、`downloadSceneJson` |
| 静态 JS | 含 `renderSceneProgress`、`applySuggestedToCurrentScene`、`downloadCurrentSceneJson` 和按 predicate 导出逻辑 |
| 静态 CSS | 含场景进度、进度条和按钮禁用态样式 |
| JS 初始化 | 在含场景包的最小 DOM/fetch stub 下动态导入执行通过 |

## 复核进度命令行报告

本轮新增命令行进度报告脚本，用于不打开网页时快速查看 draft 审批进展、优先级剩余量、场景剩余量和下一批处理清单。该脚本只读 draft 和场景包，不修改审批文件。

新增文件：

| 文件 | 用途 |
|---|---|
| `scripts/report_ch10_ch11_source_review_progress.py` | 生成第10、11章 Source_Chunks 人工复核进度报告 |
| `output/ch10_ch11_source_review_progress_2026-06-05.json` | 结构化进度报告 |
| `output/ch10_ch11_source_review_progress_2026-06-05.md` | 人工阅读版进度报告 |

当前进度：

| 项目 | 结果 |
|---|---:|
| 总条目 | 51 |
| 已填写 | 5 |
| 未填写 | 46 |
| 完成率 | 9.8% |
| P1 ch10 quick confirm | 4/4 |
| P1 ch10 formula gap | 1/1 |
| P2 ch10 boundary/summary | 0/8 |
| P2 ch11 quick confirm | 0/1 |
| P3 ch11 application scene | 0/29 |
| P4 ch11 boundary/summary | 0/8 |

下一批建议优先处理 `P2_ch10_boundary_summary` 的 8 条，然后处理 `P2_ch11_quick_confirm` 1 条，再进入 ch11 场景分组批处理。

## ch10 P2 边界/摘要复核包与建议草案

本轮继续推进第10章 Source_Chunks 人工复核准备，针对 `P2_ch10_boundary_summary` 的 8 条待复核项新增独立复核包和非正式建议草案。该草案只用于人工预审，不会被 `normalize_ch10_ch11.py` 默认读取，也没有写入正式审批文件。

新增文件：
| 文件 | 用途 |
|---|---|
| `scripts/build_ch10_p2_source_review_packet.py` | 生成第10章 P2 边界片段/教学摘要复核包 |
| `scripts/build_ch10_p2_proposed_approvals.py` | 基于当前 draft 叠加 P2 自动建议，生成非正式 proposed 审批草案 |
| `output/ch10_p2_source_review_packet_2026-06-05.json` | 结构化 P2 复核包，含候选段落和前后文 |
| `output/ch10_p2_source_review_packet_2026-06-05.md` | 人工阅读版 P2 复核报告 |
| `output/ch10_p2_source_review_packet_2026-06-05.csv` | 表格版 P2 复核清单 |
| `data/review/ch10_p2_source_boundary_manual_approvals.proposed.json` | 非正式建议草案，不作为 formal 输入 |

P2 分级结果：
| 类型 | 数量 | 建议 decision |
|---|---:|---|
| 边界片段复核 | 5 | `confirm_boundary_fragment` |
| 教学摘要术语支撑复核 | 3 | `confirm_teaching_summary` |
| 合计 | 8 | - |

建议草案结果：
| 项目 | 数量 |
|---|---:|
| 全文件 decision 条目 | 51 |
| 已有/建议非空 decision | 13 |
| 本轮新增 P2 建议 | 8 |
| `confirm_boundary_fragment` | 5 |
| `confirm_teaching_summary` | 3 |
| 继承已有 `confirm_candidate_anchor` | 4 |
| 继承已有 `manual_anchor_pending` | 1 |

验证结果：
| 检查项 | 结果 |
|---|---|
| 脚本编译 | `py -m py_compile scripts/build_ch10_p2_source_review_packet.py scripts/build_ch10_p2_proposed_approvals.py` 通过 |
| 复核包生成 | 8 条 P2 全部进入 JSON/Markdown/CSV |
| proposed 校验 | `py scripts/validate_ch10_ch11_source_manual_approvals.py --approvals data/review/ch10_p2_source_boundary_manual_approvals.proposed.json` 返回 `ok=true`，errors=0，warnings=0 |
| 正式审批文件 | `data/review/ch10_ch11_source_boundary_manual_approvals.json` 仍未创建 |

## ch11 P2 快速确认复核包与累积建议草案

本轮继续处理 `P2_ch11_quick_confirm` 的 1 条待复核项 `ch11_src_046`。该条属于 `candidate_anchor_review`，候选 Word 段落为 5362-5364，建议作为概念锚点确认。新增的累积 proposed 文件以上一轮 `ch10_p2` proposed 为基础，叠加本轮 ch11 P2 建议，仍然不作为 formal 输入。

新增文件：
| 文件 | 用途 |
|---|---|
| `scripts/build_ch11_p2_quick_review_packet.py` | 生成第11章 P2 快速确认复核包 |
| `scripts/build_ch10_ch11_p2_proposed_approvals.py` | 生成覆盖 P1、ch10 P2、ch11 P2 的累积非正式 proposed 草案 |
| `output/ch11_p2_quick_source_review_packet_2026-06-05.json` | 结构化 ch11 P2 复核包，含候选段落和前后文 |
| `output/ch11_p2_quick_source_review_packet_2026-06-05.md` | 人工阅读版 ch11 P2 复核报告 |
| `output/ch11_p2_quick_source_review_packet_2026-06-05.csv` | 表格版 ch11 P2 复核清单 |
| `data/review/ch10_ch11_p2_source_boundary_manual_approvals.proposed.json` | 累积非正式建议草案，不作为 formal 输入 |

本轮分级结果：
| 类型 | 数量 | 建议 decision |
|---|---:|---|
| ch11 候选概念锚点复核 | 1 | `confirm_candidate_anchor` |

累积 proposed 结果：
| 项目 | 数量 |
|---|---:|
| 全文件 decision 条目 | 51 |
| 累积非空 decision | 14 |
| 本轮新增 ch11 P2 建议 | 1 |
| 累积 `confirm_candidate_anchor` | 5 |
| 累积 `confirm_boundary_fragment` | 5 |
| 累积 `confirm_teaching_summary` | 3 |
| 累积 `manual_anchor_pending` | 1 |

验证结果：
| 检查项 | 结果 |
|---|---|
| 脚本编译 | `py -m py_compile scripts/build_ch11_p2_quick_review_packet.py scripts/build_ch10_ch11_p2_proposed_approvals.py` 通过 |
| 复核包生成 | 1 条 `P2_ch11_quick_confirm` 进入 JSON/Markdown/CSV |
| proposed 校验 | `py scripts/validate_ch10_ch11_source_manual_approvals.py --approvals data/review/ch10_ch11_p2_source_boundary_manual_approvals.proposed.json` 返回 `ok=true`，errors=0，warnings=0 |
| 正式审批文件 | `data/review/ch10_ch11_source_boundary_manual_approvals.json` 仍未创建 |
