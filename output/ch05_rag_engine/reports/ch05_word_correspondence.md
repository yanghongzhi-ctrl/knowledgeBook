# ch05 Source_Chunks 与 Word 正式稿对应关系报告

说明：第五章 Source_Chunks 多为知识摘要，本报告建立概念依据对应关系，不将摘要标记为教材逐字原文。

## 结果概览

- Source_Chunks：148
- 高置信度：11
- 人工确认：131
- 中置信度：0
- 待人工复核：6
- 已回写确认项：是

## 待人工复核

| Chunk | 标题 | 分数 | 候选行 | 候选文本 |
|---|---|---:|---:|---|
| `ch05_src_025` | LDP比例因子优化均衡 | 0.213 | 107 | （3）比例因子的优化均衡 |
| `ch05_src_052` | 点缓冲区 | 0.171 | 191 | 点、线、面的缓冲区 叠加分析 |
| `ch05_src_053` | 线缓冲区 | 0.183 | 191 | 点、线、面的缓冲区 叠加分析 |
| `ch05_src_054` | 面缓冲区 | 0.178 | 191 | 点、线、面的缓冲区 |
| `ch05_src_059` | 多边形叠加分析 | 0.367 | 211 | 多边形叠加分析 5.栅格图层叠加（地图代数） |
| `ch05_src_085` | 空间权重矩阵 | 0.136 | 291 | 空间分布模式 全局莫兰指数 (Global Moran's I) 全局莫兰指数（Global Moran's I）是应用最广泛的全局空间自相关统计量，用于测度属性在整个区域内的聚集或离散程度。全局莫兰... |

## 中置信度待确认

| Chunk | 标题 | 分数 | 候选行 | 候选文本 |
|---|---|---:|---:|---|
| - | 无 | - | - | - |

## 高置信度示例

| Chunk | 标题 | 分数 | 正式稿行 | 匹配依据 |
|---|---|---:|---:|---|
| `ch05_obj_01` | 学习目标 | 1.000 | 3 | objective_number_match:1 |
| `ch05_obj_02` | 学习目标 | 1.000 | 4 | objective_number_match:2 |
| `ch05_obj_03` | 学习目标 | 1.000 | 5 | objective_number_match:3 |
| `ch05_obj_04` | 学习目标 | 1.000 | 6 | objective_number_match:4 |
| `ch05_src_034` | 空间分辨率 | 0.599 | 124 | title_contains:0.88；definition:0.73；terms:空间分辨率,栅格 |
| `ch05_src_064` | 地图代数 | 0.575 | 221 | title_contains:0.88；definition:0.42；summary:0.21；terms:地图代数,两期,DEM |
| `ch05_src_068` | 欧氏距离 | 0.562 | 232 | title_contains:0.88；definition:0.56；terms:欧氏距离,点的几何距离 |
| `ch05_src_090` | 确定性插值 | 0.565 | 321 | title_contains:0.88；definition:0.29；summary:0.21；terms:确定性插值,地统计,空间自相关,插值,确定性插值依赖距离或数学,模型直观 |
| `ch05_src_097` | 块金值 Nugget | 0.593 | 344 | title_contains:0.88；definition:0.52；summary:0.17；terms:块金值,Nugget,异函数的值,差显著 |
| `ch05_src_127` | 单源单终点最短路径 | 0.617 | 445 | title_contains:0.88；definition:0.67；summary:0.13；terms:单源单终点最短路径,最短路径,单源单终点最短路径计算给 |
| `ch05_src_129` | 全对最短路径 | 0.734 | 447 | title_contains:0.88；definition:1.00；summary:0.12；terms:全对最短路径,最短路径,Dijkstra,A*,全对最短路径计算任意两个,节点之间的最优路径 |

## 人工确认示例

| Chunk | 标题 | 正式稿行 | 复核说明 |
|---|---|---:|---|
| `ch05_src_001` | GIS的定义 | 11-13 | GIS definition and road-engineering role are directly described. |
| `ch05_src_002` | GIS硬件组成 | 14-15 | GIS hardware component and equipment examples are directly described. |
| `ch05_src_003` | GIS软件组成 | 16-17 | GIS software component and platform examples are directly described. |
| `ch05_src_004` | GIS数据组成 | 18-19 | GIS data component and spatial/attribute/metadata examples are directly described. |
| `ch05_src_005` | GIS方法组成 | 20-21 | GIS methods component and spatial reasoning role are directly described. |
| `ch05_src_006` | GIS人员组成 | 22-23 | GIS personnel component and implementation role are directly described. |
| `ch05_src_007` | 位置问题 Location | 27-28 | Location question definition and road-engineering examples are directly described. |
| `ch05_src_008` | 条件问题 Condition | 29-30 | Condition question definition and screening examples are directly described. |
| `ch05_src_009` | 变化趋势问题 Trend | 31-32 | Trend question definition and temporal-change examples are directly described. |
| `ch05_src_010` | 模式问题 Pattern | 33-34 | Pattern question definition and spatial arrangement examples are directly described. |
| `ch05_src_011` | 模型问题 Model | 35-36 | Model question definition and minimum-cost path example are directly described. |
| `ch05_src_012` | GIS数据采集 | 41-43 | GIS data acquisition sources, modules and quality role are directly described. |
| `ch05_src_013` | GIS数据管理 | 44-46 | GIS data management tasks and database support role are directly described. |
| `ch05_src_014` | GIS空间分析与建模 | 47-49 | GIS spatial analysis and modeling scope and decision role are directly described. |
| `ch05_src_015` | GIS表达与可视化 | 50-52 | GIS visualization expression methods and collaboration role are directly described. |
| `ch05_src_016` | 空间参照系统 | 54-55 | Spatial reference system necessity and GIS analysis accuracy role are directly described. |
| `ch05_src_017` | 地图投影 | 57-57 | Map projection definition, distortion and trade-off are directly described. |
| `ch05_src_018` | 按投影面形状分类 | 65-69 | Projection classification by projection surface and three types are directly listed. |
| `ch05_src_019` | 按投影轴向分类 | 72-76 | Projection axis classification and engineering suitability are directly described. |
| `ch05_src_020` | 按变形性质分类 | 79-84 | Projection classification by deformation property and main types are directly listed. |
| `ch05_src_021` | 标准投影在长距离道路工程中的局限 | 87-95 | Standard projection limitations for long linear road projects are directly described. |
| `ch05_src_022` | 低失真投影 LDP | 96-97 | LDP concept and engineering precision purpose are directly described. |
| `ch05_src_023` | LDP贴合性投影轴线设计 | 98-104 | LDP fitted projection axis design and deformation-control logic are directly described. |
| `ch05_src_024` | LDP投影参考面高程优化 | 105-106 | LDP reference-plane elevation optimization is directly described. |
| `ch05_src_026` | 空间数据模型 | 113-130 | Object, field/raster and network spatial data models are directly described. |
| `ch05_src_027` | 矢量数据模型 | 115-120 | Vector model and point-line-polygon examples are directly described. |
| `ch05_src_028` | 点要素 | 116-116 | Point feature definition and examples are directly described. |
| `ch05_src_029` | 线要素 | 117-117 | Line feature definition and road-centerline example are directly described. |
| `ch05_src_030` | 面要素 | 118-118 | Polygon feature definition and land-use/expropriation examples are directly described. |
| `ch05_src_031` | TIN作为矢量表面模型 | 119-119 | TIN as a vector surface model and road terrain-expression use are directly described. |
| `ch05_src_032` | 栅格数据模型 | 121-126 | Raster model logic, core concepts, advantages and limits are directly described. |
| `ch05_src_033` | 像元 | 122-126 | Raster cell, resolution, cell value and raster model properties are directly described. |
| `ch05_src_035` | 网络模型 | 127-130 | Network model structure, use and limitations are directly described. |
| `ch05_src_036` | 拓扑关系 | 133-140 | Topology concept, types and GIS analysis role are directly described. |
| `ch05_src_037` | 邻接关系 | 136-137 | Adjacency topology relationship is directly described. |
| `ch05_src_038` | 连通关系 | 136-140 | Connectivity is directly described as a core topology relationship; impedance and turn-rule discussion is treated as network-dataset extension, not verbatim support within this span. |
| `ch05_src_039` | 包含关系 | 136-140 | Containment topology relationship and road-engineering use are directly described. |
| `ch05_src_040` | 拓扑节点表 | 141-143 | Topology node table and coordinate storage are directly described. |
| `ch05_src_041` | 拓扑弧段表 | 144-144 | Topology arc table and key relational fields are directly described. |
| `ch05_src_042` | 拓扑多边形表 | 145-145 | Topology polygon table and boundary arc list are directly described. |
| `ch05_src_043` | GIS拓扑模型与BIM构件模型差异 | 147-168 | GIS topology model and BIM component model differences are directly described. |
| `ch05_src_044` | 空间分析 | 170-170 | Spatial analysis definition and data-driven design role are directly described. |
| `ch05_src_045` | 矢量数据空间分析 | 172-173 | Vector spatial analysis scope and basic operations are directly described. |
| `ch05_src_046` | 空间查询 | 174-182 | Spatial query categories and compound query are directly described. |
| `ch05_src_047` | 按属性查询 | 176-177 | Attribute query definition and example are directly described. |
| `ch05_src_048` | 按位置查询 | 178-179 | Location query definition and example are directly described. |
| `ch05_src_049` | 复合查询 | 181-183 | Compound query with multiple spatial and attribute constraints is directly described. |
| `ch05_src_050` | 地址匹配 | 184-184 | Address matching and road safety application are directly described. |
| `ch05_src_051` | 缓冲区分析 | 186-190 | Buffer analysis concept, formula and road-engineering impact examples are directly described. |
| `ch05_src_055` | 叠加分析 | 192-213 | Overlay analysis concept and major overlay categories are directly described. |
