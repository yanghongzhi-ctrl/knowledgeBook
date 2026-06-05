# Evidence Quality Audit

This report summarizes automated textbook evidence grading. Low confidence entries are quality buckets, not approval blockers.

## Chapter Summary

| Chapter | Sources | Source Confidence | Source Needs Anchor | Answers | Answer Support | Answer Needs Anchor | Release | Field Issues |
|---|---:|---|---:|---:|---|---:|---|---|
| ch01 | 31 | ungraded=31 | 0 | 112 | ungraded=112 | 0 | released | - |
| ch02 | 110 | ungraded=110 | 0 | 150 | ungraded=150 | 0 | released | - |
| ch03 | 110 | ungraded=110 | 0 | 181 | ungraded=181 | 0 | released | - |
| ch04 | 130 | high=110, medium=20 | 0 | 254 | ungraded=254 | 0 | released | - |
| ch05 | 148 | medium=148 | 0 | 239 | ungraded=239 | 0 | released | - |
| ch06 | 150 | high=94, low=24, medium=32 | 24 | 180 | direct_word_question_hit=94, teaching_rewrite_supported_by_task_or_kp=86 | 0 | released | - |
| ch07 | 150 | low=90, medium=60 | 90 | 265 | direct_word_question_hit=265 | 0 | released | - |
| ch08 | 160 | low=92, medium=68 | 92 | 262 | direct_word_question_hit=6, teaching_rewrite_supported_by_concept_comparison=4, teaching_rewrite_supported_by_task_or_kp=252 | 0 | released | - |
| ch09 | 150 | high=119, low=2, medium=29 | 2 | 256 | direct_word_question_hit=2, teaching_rewrite_supported_by_concept_comparison=15, teaching_rewrite_supported_by_task_or_kp=203, word_direct_question_missing=36 | 36 | released | - |
| ch10 | 160 | high=129, low=1, medium=30 | 1 | 308 | ungraded=308 | 0 | released | - |
| ch11 | 160 | high=97, low=29, medium=34 | 29 | 295 | ungraded=295 | 0 | released | - |

## Attention Buckets

- `ch06` text_issue: source_repair_placeholder=9 samples=ch06_src_045,ch06_src_051,ch06_src_058,ch06_src_060,ch06_src_065

## Follow-Up Candidates

### ch06
- Source `ch06_src_009`: low / auto_operation_summary_not_direct_quote / 
- Source `ch06_src_018`: low / auto_operation_summary_not_direct_quote / 
- Source `ch06_src_026`: low / auto_operation_summary_not_direct_quote / 
- Source `ch06_src_027`: low / auto_operation_summary_not_direct_quote / 
- Source `ch06_src_028`: low / auto_operation_summary_not_direct_quote / 
- Source `ch06_src_029`: low / auto_operation_summary_not_direct_quote / 
- Source `ch06_src_030`: low / auto_operation_summary_not_direct_quote / 
- Source `ch06_src_031`: low / auto_operation_summary_not_direct_quote / 

### ch07
- Source `ch07_src_002`: low / auto_operation_summary_not_direct_quote / 纬地采用项目文件夹管理设计文件，新建项目时需设置项目名称、路径和平面线文件。
- Source `ch07_src_003`: low / auto_operation_summary_not_direct_quote / 项目管理器可查看和修改文件路径、项目属性、图框和表格模板。
- Source `ch07_src_005`: low / auto_operation_summary_not_direct_quote / 如果数模边界或三角网不理想，可通过优化数模边界或三角网优化进行修正。
- Source `ch07_src_008`: low / auto_operation_summary_not_direct_quote / 构网后应检查数模范围，必要时排除高程异常点。
- Source `ch07_src_009`: low / auto_operation_summary_not_direct_quote / 平面设计需输入路线控制条件，设置圆曲线和缓和曲线参数，完成中线线形。
- Source `ch07_src_010`: low / auto_operation_summary_not_direct_quote / S型、卵形、C型和回头曲线等组合要求设计者理解曲线连接关系和软件处理差异。
- Source `ch07_src_012`: low / auto_operation_summary_not_direct_quote / 基本模式法用于处理直线与圆、圆与圆之间的连接关系。
- Source `ch07_src_013`: low / auto_operation_summary_not_direct_quote / 纵断面地面线可由外业中桩高程输入，也可从数模内插。

### ch08
- Source `ch08_src_004`: low / auto_operation_summary_not_direct_quote / 平面设计可采用交点法和积木法，前者强调交点控制，后者适合复杂线元组合。
- Source `ch08_src_005`: low / auto_operation_summary_not_direct_quote / 纵断面设计通过Profile View、高程控制点投影、交点法或积木法完成拉坡和竖曲线设置。
- Source `ch08_src_006`: low / auto_operation_summary_not_direct_quote / 模板编辑器通过点、空点、组件、约束和末端条件组织横断面构造。
- Source `ch08_src_007`: low / auto_operation_summary_not_direct_quote / End Condition及其Priority用于复杂地形中自动选择挖方、填方、挡墙等放坡方案。
- Source `ch08_src_009`: low / auto_operation_summary_not_direct_quote / 加宽表和超高区间/车道通过规则与廊道关联，驱动曲线路段宽度和横坡变化。
- Source `ch08_src_010`: low / auto_operation_summary_not_direct_quote / 三维漫游和组件数量报表用于检查模型效果并提取材料与土石方数量。
- Source `ch08_src_011`: low / auto_operation_summary_not_direct_quote / 标注样式、标注组和命名边界支撑平面图、纵断面图的自动化出图。
- Source `ch08_src_016`: low / auto_operation_summary_not_direct_quote / 平面设计可采用交点法和积木法，前者强调交点控制，后者适合复杂线元组合。

### ch09
- Source `ch09_src_094`: low / auto_operation_summary_not_direct_quote / 曲面纵断面即纵断面地面线。在“常用”面板“纵断面”菜单下，选取“创建曲面纵断面”，弹出“从曲面创建纵断面”对话框，如图 9-12所示。用户在对话框中选定要创建纵断面的路线及路线所在的曲面后，点击“确定”即可。
- Source `ch09_src_135`: low / auto_operation_summary_not_direct_quote / 完成道路平纵横设计后，选择“常用”选项卡下“创建设计”面板中的“道路”命令。在“创建道路”对话框中指定道路名称、路线、纵断面和装配，点击“确定”完成道路创建。
- Answer `ans_ch09_116`: word_direct_question_missing / 构建地质风险影响因子图层怎么做？
- Answer `ans_ch09_117`: word_direct_question_missing / 构建综合成本表面怎么做？
- Answer `ans_ch09_119`: word_direct_question_missing / 搜索最小成本路径怎么做？
- Answer `ans_ch09_120`: word_direct_question_missing / 构建参数化道路模型怎么做？
- Answer `ans_ch09_121`: word_direct_question_missing / 生成道路重构DEM怎么做？
- Answer `ans_ch09_122`: word_direct_question_missing / 扰动后地质风险再预测怎么做？
- Answer `ans_ch09_123`: word_direct_question_missing / 候选路线方案定量比选怎么做？
- Answer `ans_ch09_125`: word_direct_question_missing / 配置空间推理触发规则怎么做？

### ch10
- Source `ch10_src_140`: low / auto_anchor_missing_or_weak / 当 且 ,则生成工程语义事实：，。

### ch11
- Source `ch11_src_117`: low / auto_anchor_missing_or_weak / 对于山区高墩桥梁或跨海大桥，数字孪生设计场景引入了风场仿真，这是跨桥梁、交通与气象多专业的综合协同体现。 （1）风致振动响应推演 结合区域气象站的长期观测数据，模拟峡谷风、强侧风或台风等典型风场条件，分析结构在不同工况下……
- Source `ch11_src_119`: low / auto_anchor_missing_or_weak / 传统道路设计通常采用人工主导的“试错式”方案比选方式，设计空间有限且依赖经验判断。数字孪生融合算法驱动、知识驱动与数据驱动等人工智能范式，推动道路设计从“辅助绘图”向“生成式设计”转变。 1.算法驱动的参数化自动布局 设……
- Source `ch11_src_121`: low / auto_anchor_missing_or_weak / 依托第二节所述的数字主线机制，路线位置或控制参数的调整将自动触发桥梁、隧道等相关构件模型的同步更新，确保整体设计方案的一致性与完整性。 2.数据与知识驱动的辅助决策 在方案生成与筛选过程中，系统综合运用数据挖掘与知识推理……
- Source `ch11_src_122`: low / auto_anchor_missing_or_weak / （1）参数智能推荐（数据驱动） 基于历史项目数据，系统可采用协同过滤或基于内容的推荐方法，为当前项目提供曲线半径、缓和曲线长度等参数建议，有效缓解设计初期的信息不足问题。 （2）规范符合性自动核查（知识驱动）
- Source `ch11_src_124`: low / auto_anchor_missing_or_weak / 虚拟驾驶仿真与安全评价 为系统评估设计方案的行车安全性与舒适性，数字孪生支持在高保真虚拟环境中开展虚拟试驾，实现安全风险的前置识别与验证。 1.三维视距连续性检验
- Source `ch11_src_125`: low / auto_anchor_missing_or_weak / 基于高精度语义模型，系统可从驾驶员视角对行车轨迹进行连续扫描。 （1）动态视距核查 系统能够识别边坡、植被及交通设施对视线的遮挡情况，连续检测停车视距与超车视距，并自动标注潜在视距受限路段。
- Source `ch11_src_126`: low / auto_anchor_missing_or_weak / （2）视觉诱导性评价 从驾驶心理与视觉感知角度，对线形组合的平顺性及交通标志布设效果进行评价，为优化行车诱导条件提供依据。 2.复杂工况下的车辆动力学仿真
- Source `ch11_src_127`: low / auto_anchor_missing_or_weak / 引入车辆动力学模型，在虚拟数字路面上模拟车辆在不同工况下的运行状态，以较低的仿真成本开展多轮安全性验证。 （1）侧滑与侧翻风险分析 模拟重载车辆或危化品运输车辆在大坡度、急弯或恶劣气象条件下的行驶性能，计算侧向加速度与轮……
