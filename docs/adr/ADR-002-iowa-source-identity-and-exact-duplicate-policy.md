# ADR-002：Iowa 源行标识与精确重复行处理

- Status: Accepted
- Date: 2026-09-01
- Scope: `iowa_liquor_snapshot_2026_07_v1` 的事实表主键和数据质量处理

## Context

官方目录将 `invoice_id` 描述为订单行唯一标识，但对 2024–2026-07 官方导出首次画像发现：同一 `invoice_id` 可关联多条产品行。因此它是发票/订单头标识，不能作为事实行主键。

画像还发现 20 组逐字段完全相同的原始行。如果直接求和，这些副本会重复累计批发销售额和数量。

## Decision

1. `invoice_id` 保留为业务来源字段，语义为发票标识；不设为 `fact_liquor_order_line` 主键。
2. `source_record_id` 使用全部影响业务含义的源字段的内容指纹（SHA-256）。事实粒度为“可区分的订单商品行”。
3. 只移除 `source_record_id` 相同的逐字段完全相同原始副本；不按发票、商品、日期或金额进行模糊去重。
4. 原始文件永远不改写。`raw_row_count`、`exact_duplicate_raw_rows`、逻辑事实行数和去重规则版本必须进入 manifest、Trace 和 Evidence provenance。
5. 如果未来出现无法由完整源字段区分但业务上不同的行，数据管道必须停止并进入 `REJECTED`，而不是猜测合并规则。

## Consequences

- 所有汇总以去除精确副本后的逻辑事实表为准。
- 该决策修正了前置文本中“`invoice_id` 全局唯一”的不准确假设，不改变产品的只读、证据可追溯或事件时间真相原则。
- 后续接入含原生行号的企业源时，应优先使用源系统不可变行 ID，并在其 Context Package 中声明。
