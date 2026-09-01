# ADR-001：MVP 主数据集与双轨评测数据策略

> Status: Accepted  
> Date: 2026-09-01  
> Decision Owners: Product Architecture / Data Agent Architecture  
> Affects: Architecture Baseline、MVP Vertical Slice、Phase 0 Contracts and Benchmark

实施级数据契约：[MVP 数据基础冻结设计](../data-foundation-design.md)

## 1. 决策摘要

MVP 主公开数据域冻结为：

> **Iowa Liquor Wholesale Intelligence**：基于 Iowa Department of Revenue 发布的 Iowa Liquor Sales 数据，分析 Iowa 州酒类管理体系向 Class E 持牌门店发生的批发采购/订单活动。

旗舰问题冻结为：

> 2026 年 7 月 Iowa 酒类批发销售额和批发价差较 6 月及去年同期发生了什么变化？哪些 Store、County、Vendor、Category 和 Product 是主要贡献来源？变化可由数量、单位批发价还是产品结构解释到什么程度？

同时冻结“双轨数据策略”：

1. **Official Snapshot Track**：固定版本的 Iowa 官方数据快照，用于真实世界分析展示、确定性数值评测和来源追踪。
2. **Controlled Fixture Track**：小规模确定性合成夹具，用于权限、缺失映射、重复 Join、数据陈旧、无主导因素和恢复等不可依赖公开数据稳定触发的测试。

Iowa 数据替代原来的虚构电商订单域，成为 MVP 的主公开演示数据；合成数据不再承担产品故事，但继续承担受控故障与边界评测。

## 2. 为什么接受该数据集

Iowa 官方目录给出的数据具备以下特征：

- 交易视图覆盖 2012 年 1 月至当前最近月份，按月更新；
- 记录 Class E liquor licensees 按产品、门店和日期发生的 spirits purchase information；
- 2026 年数据截至 2026-07-31，共 1,402,652 行；
- 2012 至当前的合并视图截至同一日期共 34,660,619 行；
- Store 和 Product 参考数据分别约有 3,041 和 13,592 行；
- 当前 Iowa Data Hub 目录将相关资产标为公开并采用 CC BY 许可。

官方来源：

- [Iowa Liquor Sales, January 2012 - Current](https://data.iowa.gov/catalog/dataset/1051)
- [Iowa Liquor Sales, 2026](https://data.iowa.gov/catalog/dataset/1263)
- [Iowa Liquor Stores](https://data.iowa.gov/catalog/dataset/1028)
- [Iowa Liquor Products](https://data.iowa.gov/catalog/dataset/1029)

该数据域比常见的小型教学数据更能展示：大规模事实表、时间比较、指标派生、多维下钻、贡献分解、语义歧义处理、数据质量检查和 Evidence Provenance。

## 3. 必须采用的业务语义

### 3.1 数据代表什么

该事实数据代表 Iowa Class E 持牌门店从州酒类管理体系发生的产品采购/批发订单活动。

它不直接代表：

- 终端消费者 POS 销售；
- 门店面向消费者的真实零售价；
- 门店利润或净利润；
- 消费者、会员或 Customer Segment 行为；
- 退款、优惠券、营销转化或电商渠道行为。

源字段 `state_bottle_retail` 的官方含义是门店每瓶支付金额。产品界面和语义包不得因为字段名含有 `retail`，将其解释为消费者货架零售价。

### 3.2 MVP 核心指标

| Metric ID | 冻结定义 | 语义限制 |
| --- | --- | --- |
| `wholesale_sales_amount` | `SUM(sales_dollars)` | 门店采购订单金额/州批发销售额，不是消费者零售额 |
| `state_acquisition_cost` | `SUM(ROUND(state_bottle_cost * sales_bottles, 2))` | 州方按交易行估算的商品取得成本 |
| `wholesale_gross_spread` | `wholesale_sales_amount - state_acquisition_cost` | 批发价差，不得表述为门店利润或完整会计利润 |
| `wholesale_spread_rate` | `wholesale_gross_spread / wholesale_sales_amount` | 分母为零时返回不可计算 |
| `bottles_ordered` | `SUM(sales_bottles)` | 门店订购瓶数，不等于消费者售出瓶数 |
| `volume_liters` | `SUM(sales_liters)` | 订购产品体积 |
| `avg_wholesale_price_per_bottle` | `wholesale_sales_amount / bottles_ordered` | 组合均价，会受到产品 Mix 影响 |
| `avg_state_cost_per_bottle` | `state_acquisition_cost / bottles_ordered` | 组合成本均值 |

所有金额采用数据源记录币种，并在语义包中明确精度。任何关于“盈利”的用户问题都必须澄清，是询问 `wholesale_gross_spread`，还是系统并不拥有的企业会计利润。

### 3.3 MVP 核心维度

- `order_date` / month / year；
- `store`；
- `county` / city；
- `vendor`；
- `category`；
- `item` / product；
- `pack`；
- `bottle_volume`。

MVP 不声明存在 `channel` 或 `customer_segment` 维度。

## 4. 快照与可复现性决策

### 4.1 基准窗口

首个 Official Snapshot 目标窗口冻结为：

- `dataset_version = iowa_liquor_snapshot_2026_07_v1`；
- `2024-01-01` 至 `2026-07-31`；
- 来源为合并销售视图；
- 支持 2026 年 7 月环比、同比和滚动趋势比较；
- v1 中的“最新完整月份”固定解析为 2026 年 7 月；
- 实际提取时必须再次记录源资产版本、最大业务日期、行数和 fingerprint。

官方 Schema 明确标注 `state_bottle_cost` 和 `state_bottle_retail` 在 2025-07-01 前不可用。因此 2024 起的数据用于销售额、瓶数、体积和 Mix 趋势；成本与批发价差只能用于所有比较期间均不早于 2025-07-01 的分析。v1 的 2026 年 7 月环比和同比符合该条件。

产品可以提供 `iowa_liquor_rolling` 逻辑别名选择最近一个 `READY` Snapshot，但该别名不是数据版本。Task 创建时必须将其解析为具体不可变 `dataset_version`；Evidence、Artifact、Golden Case 和 Evaluation Result 不得只绑定 rolling alias。

### 4.2 快照清单

每个数据版本必须保存 manifest：

- source title、catalog URL、table/asset identifier；
- extraction timestamp 和 source last-updated timestamp；
- 提取查询、时间范围和列清单；
- row count、schema fingerprint、content fingerprint；
- source maximum/minimum business date；
- license type、attribution text 和 NOTICE reference；
- 空值、重复键和异常值画像；
- 生成的 Parquet/DuckDB artifact fingerprint。

Golden Case 绑定快照 fingerprint，不能绑定“latest”或只绑定文件名。在线刷新后的数据不得静默覆盖回归基线。

### 4.3 存储策略

- 仓库保存提取规范、manifest、小型 fixture 和必要样本；
- 大型官方 Raw/Curated 数据默认不直接提交 Git；
- 本地分析版本采用列式快照并由 DuckDB 读取；
- 是否分发完整快照取决于仓库大小、GitHub 发布方式和 CC BY 归属要求，进入实现前单独确认。

## 5. 事实表与参考数据的时间语义

销售事实中已经包含交易发生时记录的 Store、County、Vendor、Category 和 Item 等属性。当前 Store/Product 数据集按月更新，但目录未说明它们提供完整的 Slowly Changing Dimension 历史。

因此冻结以下优先级：

1. 历史分析以销售事实行内属性作为 event-time truth；
2. Store/Product 当前表物理命名为 `dim_store_current` 和 `dim_product_current`，仅用于补充当前状态或事实中不存在的属性；
3. 当前维表不得覆盖历史事实属性；
4. Join 前必须验证唯一性、缺失率和一对多风险；
5. 发现代码复用、类别变更或历史不一致时，保留原始事实值并产生 Data Quality Warning。

这一规则防止使用“今天的维度快照”错误重写过去的经营语义。

## 6. 分析与结论边界

MVP 可以确定性回答：

- 金额、瓶数、体积和批发价差发生了多少变化；
- 哪些维度成员对总变化贡献最大；
- 数量、组合均价和产品 Mix 的数学分解；
- 分解是否可对账、数据是否完整、新鲜度是否满足要求。

MVP 不能仅凭该数据证明：

- 终端消费者需求为何变化；
- 某营销、天气、政策或竞争事件造成了变化；
- 门店最终销售或利润发生同等变化；
- 贡献关系已经构成因果关系。

因此主流程使用“贡献来源”“相关驱动因素”“可由数据解释的部分”，不用“已证明根因”。若需要外部事件解释，应作为后续可选 Context Source，并明确 Evidence 等级。

## 7. Golden Case 与演示数据的分工

### Official Snapshot Track

用于：

- 真实业务问题和旗舰 Demo；
- 指标、时间、过滤、粒度、SQL 和数值正确性；
- 贡献分解、Mix 分析和 Claim-Evidence-Provenance；
- 真实缺失值和分布下的鲁棒性。

在快照冻结后，数值答案必须由独立的确定性参考计算生成和复核。Agent 在运行时不知道答案，不意味着评测系统可以不知道答案。

### Controlled Fixture Track

用于稳定触发：

- 未授权 Store/County/字段访问；
- stale snapshot；
- missing dimension mapping；
- duplicate join trap；
- no-dominant-driver period；
- unsupported causal request；
- checkpoint/retry/idempotency 场景。

合成夹具必须小、可读、固定 seed，并绑定明确 ground truth。它不是第二套产品领域。

## 8. 被替换的原设计

以下原 MVP 语义不再属于主路径：

- `gross_revenue`、`discount_amount`、`refund_amount`；
- `net_revenue`、`cogs`、`gross_profit`、`gross_margin`；
- `order_count`、`average_order_value`；
- `channel`、`customer_segment`；
- 华南电商毛利润下降的旗舰场景。

如果未来增加真实电商订单域，应通过新的 Domain Semantic Package 和 ADR 引入，不能把两套指标混入当前 Iowa 语义包。

## 9. 许可与归属

当前 Iowa Data Hub 目录将上述四个资产标为 CC BY。实施时必须逐资产记录许可，不得依据旧链接、第三方镜像或整个站点的通用条款推断所有资产许可一致。

发布演示数据或派生快照时至少保留：

- “Source: Iowa Department of Revenue, Alcohol & Tax Operations Division”；
- 原始资产标题与直接链接；
- 提取和修改说明；
- 对应 CC BY 链接；
- 本项目不隶属于或代表 Iowa 州政府的说明。

## 10. 后果

正向影响：

- 产品展示建立在真实、公开、持续更新的大规模经营数据上；
- Semantic Intelligence、Context Compiler、受治理 SQL、Evidence 和 Evaluation 都有实际难度；
- 数据可以同时支持精确查询和有限自主调查。

代价和约束：

- 不能再展示退款、折扣、客户、渠道和真实门店利润分析；
- 必须增加数据提取、许可归属、快照和质量画像工作；
- “根因分析”需收敛为可对账贡献分析，除非接入额外因果证据；
- 仍需维护小型受控夹具，公开数据不能替代全部测试资产。

## 11. 后续触发条件

出现以下任一条件时重新评审本 ADR：

- 官方资产许可、字段定义或访问方式发生实质变化；
- 数据不再按可接受频率更新；
- 关键字段质量无法支撑稳定基准；
- GitHub 分发方式无法满足许可或体积要求；
- 产品决定从批发贡献分析转向消费者、电商或会计利润分析。
