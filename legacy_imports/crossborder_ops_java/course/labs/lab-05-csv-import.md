# Lab 05：扩展 CSV 导入

## 目标

把项目从“只看种子数据”扩展成“能导入学生自己的小数据”。这是扩展实验，不是第一天必须完成的功能。

## 最小版本

只支持订单 CSV，字段固定：

```csv
store_code,sku_code,order_date,quantity,net_sales,gross_profit
Amazon US Store,EB-US-1001,2026-07-01,3,89.97,55.20
```

## 推荐接口

```text
POST /training/import/orders
```

## 推荐实现

| 层级 | 文件 |
|---|---|
| Controller | 新建 `TrainingImportController.java` |
| Service | 新建 `TrainingImportService.java` |
| Repository | 复用 `StoreRepository`、`SkuProductRepository`、`CommerceOrderRepository` |

## 约束

- 先只支持 CSV，不支持 Excel。
- 先只支持新增订单，不做复杂去重。
- 每行失败要返回行号和原因。
- 不要把 CSV 解析交给大模型。

## 验收标准

- 上传 1 个合法 CSV 后，经营概览指标会变化。
- 上传缺少字段的 CSV，会返回清晰错误。
- 原有种子数据仍然可用。

## 任务分层

- 必做：导入订单 CSV。
- 进阶：返回每行导入结果。
- 挑战：支持退款 CSV。

## 提交物

1. CSV 示例文件。
2. 导入接口代码。
3. 合法 CSV 导入结果。
4. 非法 CSV 错误返回。
5. 导入前后的经营概览对比。
