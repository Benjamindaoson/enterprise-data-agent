# Enterprise Intelligence Workspace：MVP 数据基础冻结设计

> Status: Data Foundation Baseline v1.0 — FROZEN  
> Date: 2026-09-01  
> Parent: [ADR-001：MVP 主数据集与双轨评测数据策略](adr/ADR-001-primary-demo-dataset.md)  
> Scope: 数据源、快照、字段语义、Raw/Curated 模型、指标可用性、质量门槛、存储与更新契约

## 0. 冻结结论

MVP 主公开数据域冻结为 Iowa Liquor Wholesale Intelligence。

业务数据链路冻结为：

```text
Iowa Official Assets
        ↓
Immutable Source Snapshot
        ↓
Raw Parquet
        ↓
Quality Gate + Canonical Mapping
        ↓
Curated Parquet / DuckDB Views
        ↓
Versioned Domain Semantic Package
        ↓
Governed SQL + Deterministic Analysis Tools
```

控制面链路冻结为：

```text
Analysis Task / Context / Plan / Checkpoint
Observation / Claim / Evidence / Validation / Evaluation
                         ↓
                     PostgreSQL
```

Parquet/DuckDB 是业务分析数据面；PostgreSQL 是 Agent 状态、证据和评测事实来源。两者不得混用职责。

## 1. 官方源资产

| Role | Catalog ID | Official Table | Initial Source State | License | Frozen Usage |
| --- | ---: | --- | --- | --- | --- |
| Sales fact | `1051` | `liquor_sales_combined` | updated 2026-08-25；data through 2026-07-31 | CC BY | 主分析事实源 |
| Store reference | `1028` | `liquor_stores` | updated 2026-08-03；3,041 rows | CC BY | 当前门店属性补充 |
| Product reference | `1029` | `liquor_products` | updated 2026-08-02；13,592 rows | CC BY | 当前商品属性补充 |

官方入口：

- [Iowa Liquor Sales, January 2012 - Current](https://data.iowa.gov/catalog/dataset/1051)
- [Iowa Liquor Stores](https://data.iowa.gov/catalog/dataset/1028)
- [Iowa Liquor Products](https://data.iowa.gov/catalog/dataset/1029)

业务背景采用 [Iowa Alcohol Operations Listing Manual](https://revenue.iowa.gov/media/235/download?inline=) 的正式定义：Department 是面向 Class E retail alcohol licensees 的 alcoholic liquor sole wholesaler。该事实用于解释业务数据的交易双方，不扩大为消费者 POS、门店盈利或完整供应链数据。

## 2. 数据版本与时间边界

### 2.1 初始不可变基准

初始数据版本冻结为：

| Field | Value |
| --- | --- |
| `dataset_version` | `iowa_liquor_snapshot_2026_07_v1` |
| `business_date_start` | `2024-01-01` inclusive |
| `business_date_end` | `2026-08-01` exclusive |
| `data_through_date` | `2026-07-31` |
| Semantic package/version | `iowa_liquor_wholesale` / `1.0.0` |
| `default_current_period` | `2026-07-01` to `2026-07-31` |
| `default_previous_period` | `2026-06-01` to `2026-06-30` |
| `default_year_ago_period` | `2025-07-01` to `2025-07-31` |
| Business timezone | `America/Chicago` |
| Currency | `USD` |

该版本一旦生成不得被后续官方更新覆盖。重新同步产生 `v2` 或新的年月版本，并拥有新的 manifest、fingerprint 和 Golden Result Set。

### 2.2 Rolling Channel 与 Frozen Snapshot

- **Rolling Channel**：逻辑别名 `iowa_liquor_rolling`，指向最近一个已通过质量和回归门槛的不可变 Snapshot。它不是 `dataset_version`，不得被 Evidence、Claim 或 Golden Case 直接持久化。
- **Frozen Benchmark Snapshot**：`iowa_liquor_snapshot_2026_07_v1`。Reproducible Demo 和所有 Evaluation 直接绑定该不可变版本；其中 `latest complete month` 永远解析为 2026 年 7 月。
- **Freshness Candidate**：手动同步可以发现新的官方完整月份，但必须生成新的不可变候选 Snapshot，通过质量门槛和回归后，才能原子更新 Rolling Channel 的指向。

任何 Golden Case 禁止绑定无版本的 `latest`。

运行时解析 `iowa_liquor_rolling` 后，`AnalysisTask`、`AnalysisContext`、Evidence 和 Artifact 必须保存解析得到的具体 `dataset_version`，不能只保存别名。

### 2.3 双数据窗口

| Window | Range in v1 | Allowed Metrics/Analysis |
| --- | --- | --- |
| `OPERATING_TREND_WINDOW` | 2024-01-01 through 2026-07-31 | Sales、Bottles、Liters、Average Wholesale Price、Category/Vendor/Store/County、Price/Volume/Mix |
| `COST_SPREAD_WINDOW` | 2025-07-01 through 2026-07-31 | State Acquisition Cost、Wholesale Gross Spread、Wholesale Spread Rate、Average State Cost |

Metric Availability 由 Semantic Package 声明并由 Context Compiler 在当前期与每个比较期分别验证。

### 2.4 全量历史

2012 至当前的完整数据只用于后续性能与规模验证，不属于 MVP 功能验收数据。全量模式不得改变领域契约和指标定义。

## 3. 交易语义与术语

事实记录描述 Class E 门店向 Iowa 州酒类批发体系订购的商品行。

产品统一使用以下术语：

| Source/UI Ambiguity | Canonical Meaning |
| --- | --- |
| Sales | 州批发销售额 / 门店采购订单金额 |
| Bottles Sold | 门店订购瓶数 `bottles_ordered` |
| State Bottle Retail | 门店采购单价 `store_purchase_price_per_bottle` |
| State Bottle Cost | 州方每瓶取得成本 `state_cost_per_bottle` |
| Gross Spread | 州方取得成本与批发订单金额之间的价差 |

禁止将数据解释为：

- 消费者 POS 销售或消费需求；
- 门店货架零售价；
- 门店毛利、门店净利润或州政府完整会计利润；
- 已识别的退款、折扣、营销活动或顾客行为。

## 4. Raw 数据契约

Raw 层保存官方值、官方字段名和来源元数据，不做业务值修正。

### 4.1 Sales 必需字段

| Source Field | Meaning | Source Type | Required for MVP |
| --- | --- | --- | --- |
| `invoice_id` | 官方发票/订单标识；不是事实行主键 | STRING | yes |
| `ordered_on` | 订单日期 | DATE | yes |
| `store_no` / `store_name` | 门店标识/名称 | STRING | yes |
| `store_address` / `store_city` / `store_zip_code` | 交易时记录的门店地址 | STRING | no |
| `county_fips_code` / `county_name` | 交易时记录的地理属性 | STRING | no |
| `category_code` / `category_name` | 交易时记录的品类 | STRING | no |
| `vendor_number` / `vendor_name` | 交易时记录的 Vendor | STRING | no |
| `item_no` / `im_desc` | 商品标识/描述 | STRING | yes |
| `pack` / `bottle_volume_ml` | 包装与单瓶容量 | numeric | no |
| `state_bottle_cost` | 州方每瓶成本 | FLOAT in source | conditional |
| `state_bottle_retail` | 门店每瓶采购价 | FLOAT in source | conditional |
| `sales_bottles` | 门店订购瓶数 | INTEGER | yes |
| `sales_dollars` | 订单行金额 | FLOAT in source | yes |
| `sales_liters` / `sales_gallons` | 订单行体积 | FLOAT in source | no |

真实官方导出画像（2026-09-01）证明，同一 `invoice_id` 可以包含多条商品行。因此 `invoice_id` 是发票/订单标识，必须非空，但不能作为事实主键。`source_record_id` 由影响业务含义的完整源字段内容指纹生成；逐字段完全相同的 Raw 副本只可按 ADR-002 去重，并记录数量。任何非精确、无法解释的重复仍会使候选快照进入 `REJECTED`。

### 4.2 Source Metadata

每份 Raw 分区必须关联：

- catalog ID、official table 和 source URL；
- extraction timestamp；
- source `lastUpdated`；
- requested and observed date range；
- source schema fingerprint；
- raw content/file fingerprint；
- row count；
- license and attribution reference；
- extractor version and extraction parameters。

实际行数、文件 checksum 和提取时间只能在数据被真实提取后写入 manifest，不在设计文档中预造。

### 4.3 Manifest 最小契约

```yaml
dataset_version: iowa_liquor_snapshot_2026_07_v1
publish_channel_candidate: iowa_liquor_rolling
status: READY
source:
  publisher: Iowa Department of Revenue
  catalog_id: 1051
  table: liquor_sales_combined
  source_last_updated: 2026-08-25
semantic:
  package: iowa_liquor_wholesale
  version: 1.0.0
  fingerprint: GENERATED_AT_BUILD
coverage:
  start: 2024-01-01
  end_inclusive: 2026-07-31
metric_windows:
  operating_trend:
    valid_from: 2024-01-01
  cost_and_spread:
    valid_from: 2025-07-01
profiling:
  invoice_id_non_null: GENERATED_AT_BUILD
  source_record_id_unique_after_exact_deduplicate: GENERATED_AT_BUILD
  exact_duplicate_raw_rows: GENERATED_AT_BUILD
  row_count: GENERATED_AT_BUILD
  schema_fingerprint: GENERATED_AT_BUILD
  content_fingerprint: GENERATED_AT_BUILD
```

`GENERATED_AT_BUILD` 是未构建状态的占位标识。Snapshot 进入 `READY` 前必须替换为真实值；包含该占位符的 manifest 不得被 Agent 查询。

`invoice_id` 不再作为唯一性门槛。Raw 保留不变；Curated 层只依据 ADR-002 去除完整源字段均相同的副本，并把原始行数、去重数、逻辑事实行数和规则版本写入 manifest。不能由此规则解释的重复必须令 Snapshot 进入 `REJECTED`。

## 5. Curated 数据契约

### 5.1 `fact_liquor_order_line`

Grain：每个可区分的官方订单商品行一行；`invoice_id` 可跨多行重复，`source_record_id` 是稳定内容指纹。

核心映射：

| Canonical Column | Source |
| --- | --- |
| `source_record_id` | `invoice_id` |
| `order_date` | `ordered_on` |
| `store_id` | `store_no` |
| `store_name_at_order` | `store_name` |
| `county_fips_at_order` | `county_fips_code` |
| `county_name_at_order` | `county_name` |
| `category_id_at_order` | `category_code` |
| `category_name_at_order` | `category_name` |
| `vendor_id_at_order` | `vendor_number` |
| `vendor_name_at_order` | `vendor_name` |
| `product_id` | `item_no` |
| `product_name_at_order` | `im_desc` |
| `pack` | `pack` |
| `bottle_volume_ml` | `bottle_volume_ml` |
| `state_cost_per_bottle` | `state_bottle_cost` |
| `store_purchase_price_per_bottle` | `state_bottle_retail` |
| `bottles_ordered` | `sales_bottles` |
| `line_wholesale_sales_amount` | `sales_dollars` |
| `ordered_volume_liters` | `sales_liters` |

Raw FLOAT money 在 Curated 层转换为 Decimal。冻结精度：

- unit money：`DECIMAL(18,4)`；
- line/aggregate money：`DECIMAL(20,2)`；
- volume：`DECIMAL(20,4)`；
- count：`BIGINT`。

### 5.2 参考维度

- `dim_date`：本项目确定性生成。
- `dim_store_current`：来自 `liquor_stores`，主键 `store`，保留 `report_date`。
- `dim_product_current`：来自 `liquor_products`，主键 `item_no`，保留 `report_as_of`。

MVP 不建立伪历史 `dim_store`、`dim_product` 或独立 `dim_vendor`。历史聚合默认使用事实行内的 `*_at_order` 属性。当前参考维度只能用于补充当前状态、经纬度、UPC、proof 等事实中不存在的属性。

Join 规则：

1. 所有当前维度 Join 使用 `LEFT JOIN`；
2. Join 前必须通过当前维度键唯一性检查；
3. 当前维度缺失是 Coverage Warning，不删除事实行；
4. 当前维度属性不得覆盖事实行内历史属性；
5. Join 后事实行数和核心金额必须与 Join 前对账。

## 6. Metric Contract 与可用期

| Metric ID | Formula | Availability in v1 |
| --- | --- | --- |
| `wholesale_sales_amount` | `SUM(line_wholesale_sales_amount)` | 2024-01-01 onward |
| `bottles_ordered` | `SUM(bottles_ordered)` | 2024-01-01 onward |
| `volume_liters` | `SUM(ordered_volume_liters)` | 2024-01-01 onward |
| `avg_wholesale_price_per_bottle` | `wholesale_sales_amount / bottles_ordered` | 2024-01-01 onward |
| `state_acquisition_cost` | `SUM(ROUND(state_cost_per_bottle * bottles_ordered, 2))` | 2025-07-01 onward |
| `wholesale_gross_spread` | `wholesale_sales_amount - state_acquisition_cost` | 2025-07-01 onward |
| `wholesale_spread_rate` | `wholesale_gross_spread / wholesale_sales_amount` | 2025-07-01 onward |
| `avg_state_cost_per_bottle` | `state_acquisition_cost / bottles_ordered` | 2025-07-01 onward |

官方 Sales Schema 明确标注 `state_bottle_cost` 和 `state_bottle_retail` 在 2025-07-01 前不可用。因此：

- 2024 起可以分析销售额、瓶数、体积、组合均价和 Mix；
- 批发价差与州方成本只能比较所有期间均不早于 2025-07-01 的任务；
- v1 旗舰场景的 2026-07 环比与 2025-07 同比满足该条件；
- 跨越不可用区间的 Spread 请求必须返回 Metric Coverage Warning，并请求调整期间或降级为销售/数量分析；不得将空值当作零。

`state_bottle_retail * sales_bottles` 只作为 `sales_dollars` 的质量校验，不作为销售额事实来源，避免浮点和行级舍入差异。

## 7. 数据质量门槛

### 7.1 阻止发布候选快照

- 必需字段缺失；
- `invoice_id` 为空或重复；
- `ordered_on` 无法转换为日期或超出请求窗口；
- source schema 与已接受契约不兼容；
- 文件/content fingerprint 缺失；
- observed `data_through_date` 与 manifest 声明不一致；
- 核心销售额或瓶数无法完成 Raw-to-Curated 对账。

### 7.2 允许发布但必须告警

- Store/Product 当前参考表无法匹配历史事实；
- County、Category、Vendor 等非必需维度缺失；
- 2025-07-01 前成本字段为空；
- 负数量或负金额；
- 单价乘数量与 `sales_dollars` 存在超过容差的舍入差异。

负值不得在 Raw 层删除或改写。MVP 默认将其作为源系统的 signed adjustment 计入加总，但不得在没有独立字段或规则时把它描述为“退款”。若负值对结果有实质影响，生成 Data Quality/Interpretation Warning。

### 7.3 Referential Coverage

Sales → Current Store/Product 不设置会删除历史事实的强 FK。评测以下指标：

- matched fact row rate；
- matched sales amount rate；
- current dimension duplicate key count；
- fact-to-dimension reconciliation delta。

阈值必须由首次真实画像产生，经 ADR 接受后才能成为发布门槛；当前不编造百分比。

## 8. 物理存储

逻辑布局冻结为：

```text
data/
├── raw/iowa_liquor/
│   ├── sales/<dataset_version>/year=YYYY/
│   ├── stores/<dataset_version>/
│   └── products/<dataset_version>/
├── curated/iowa_liquor/<dataset_version>/
│   ├── fact_liquor_order_line/year=YYYY/
│   ├── dim_store_current/
│   ├── dim_product_current/
│   └── dim_date/
├── manifests/iowa_liquor/
└── fixtures/evaluation/
```

仓库只提交：

- 数据契约和 Schema；
- source/extraction specification；
- manifests；
- 小型、明确标记 `synthetic=true` 的 Evaluation Fixtures；
- 数据获取、构建和校验入口。

大型 Raw/Curated Parquet 不直接提交普通 Git 历史。具体 CLI/Make 命令名由开发工具链 ADR 冻结，数据设计只冻结其行为：`fetch → validate raw → build curated → validate curated → fingerprint`。

## 9. 同步与发布状态机

```text
DISCOVERED
  → INGESTING
  → RAW_CAPTURED
  → PROFILING
  → CURATING
  → VALIDATING
  → BENCHMARKING
  → READY
```

失败状态：`REJECTED`。

`READY` 是 Agent 和 Rolling Channel 唯一允许解析的数据状态。失败后生成的 fallback `source_row_id` 只用于隔离区诊断，不能绕过 `invoice_id` 唯一性失败将版本推进到 `READY`。

MVP 只支持显式手动同步。候选版本只有在以下条件全部满足后才能成为默认版本：

- Data Quality Gate 通过；
- Semantic Package 对该版本兼容；
- deterministic reference results 已生成；
- Golden Suite 通过；
- license/attribution manifest 完整；
- 默认 Demo 期间已解析为绝对日期。

平台阶段才增加月度自动发现和增量同步。

## 10. Official Snapshot 与 Controlled Fixture 的隔离

Official Snapshot：

- 不修改业务结果；
- 不注入销量、价格或 Mix 异常；
- 只用于真实经营发现和真实数据数值基准。

Controlled Fixture：

- 只用于权限、Join、质量、恢复和拒绝回答等确定性测试；
- 必须标记 `synthetic=true` 和预期 Ground Truth；
- 不得出现在旗舰 Demo 的经营结论中；
- 不得与 Official Snapshot 聚合。

“真实数据不造异常”与“系统必须测试异常路径”由此同时成立。

### 10.1 Ground Truth 冻结流程

```text
Frozen Snapshot + Semantic Version
        ↓
Independent Deterministic Query/Computation
        ↓
Expected Numeric/Ranked Result + Tolerance
        ↓
Analyst Review
        ↓
APPROVED Golden Result
```

每份 Golden Result 至少绑定：

- dataset version and content fingerprint；
- semantic package version and fingerprint；
- absolute current/comparison periods；
- reference query/computation hash；
- expected result or tolerance；
- required/forbidden Claim rules；
- reviewer、review timestamp 和 review status。

Rolling Channel 更新不会自动改写既有 Golden Result。新 Snapshot 必须生成独立的 Result Set。

## 11. 旗舰 Demo 数据契约

主 Demo 固定使用 `iowa_liquor_snapshot_2026_07_v1`：

> 分析该数据版本的最新完整月份（解析为 2026 年 7 月）Iowa 酒类批发销售表现，与 2026 年 6 月和 2025 年 7 月比较，识别 County、Category、Vendor、Store 和 Product 的主要贡献来源，并区分数量、组合均价与 Mix 变化。

必须展示：

- selected dataset version、data through date 和 freshness；
- resolved absolute periods；
- Wholesale Sales、Bottles Ordered、Average Wholesale Price 和 Wholesale Gross Spread；
- contribution and mix decomposition；
- Claim → Evidence → Query/Computation → Snapshot/Metric Version；
- 数据无法支持的原因解释和限制条件。

不得显示 `Bottles Sold`、消费者销量、门店利润或已证明根因等越界术语。

## 12. Phase 0 数据退出标准

- 三个官方源资产具有完整 source contract；
- v1 Snapshot manifest 填入真实 row count、timestamps 和 fingerprints；
- Raw 与 Curated Schema 验证通过；
- `invoice_id` 非空、必需字段检查通过；逻辑 `source_record_id` 唯一性和精确 Raw 重复行计数已验证；
- 指标可用期规则可被 Context Compiler/Evaluation 使用；
- Join 前后行数与金额可对账；
- v1 主问题具有独立生成的 deterministic result set，并保存 `reference_query_hash`、`reviewed_by`、`reviewed_at` 和 `review_status=APPROVED`；
- Controlled Fixtures 与 Official Snapshot 物理、元数据和评测标签隔离；
- CC BY attribution/NOTICE 完整；
- Golden Cases 不依赖无版本的 `latest`。

在这些条件完成前，数据域虽然已完成设计冻结，但尚未形成可发布的 Benchmark Snapshot。
