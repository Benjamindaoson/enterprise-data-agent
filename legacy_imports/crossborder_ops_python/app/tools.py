from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.metrics import MetricService


def parse_date(value: str | None, fallback: date) -> date:
    return date.fromisoformat(value) if value else fallback


def summarize_business(db: Session, start_date: str | None = None, end_date: str | None = None, store_name: str | None = None) -> str:
    end = parse_date(end_date, date.today())
    start = parse_date(start_date, end - timedelta(days=30))
    s = MetricService(db).summarize_business(start, end, store_name)
    judgement = (
        "利润率偏低，建议优先检查广告 ACOS、退款 SKU 和物流成本。"
        if s.profit_rate < Decimal("18")
        else "整体利润率可接受，建议继续拆分广告、退款和评论数据寻找增长点。"
    )
    return f"""经营概览（{s.store_name}，{s.start_date} 至 {s.end_date}）：
- 净销售额：{s.net_sales:,.2f}
- 毛利润：{s.profit:,.2f}
- 利润率：{s.profit_rate:.2f}%
- 平均订单利润：{s.average_order_profit:,.2f}
- 退款金额：{s.refund_amount:,.2f}
- 退款率：{s.refund_rate:.2f}%
- 订单数：{s.orders}
- 销售件数：{s.units}

初步判断：{judgement}"""


def refund_risks(db: Session, start_date: str | None = None, end_date: str | None = None, store_name: str | None = None, top_n: int = 5) -> str:
    end = parse_date(end_date, date.today())
    start = parse_date(start_date, end - timedelta(days=60))
    rows = MetricService(db).refund_risks(start, end, store_name, top_n)
    if not rows:
        return "该时间段内没有退款记录。"
    lines = ["退款风险 SKU 排名："]
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. {row['title']} [{row['skuCode']}]：退款 {row['refunds']} 单，"
            f"销量 {row['units']} 件，退款率 {row['refundRate']:.2f}%，退款金额 {row['refundAmount']:,.2f}"
        )
    lines.append("\n建议：优先检查排名靠前 SKU 的差评关键词、Listing 描述准确性、包装和物流破损问题。")
    return "\n".join(lines)


def high_acos_campaigns(db: Session, start_date: str | None = None, end_date: str | None = None, store_name: str | None = None, threshold_percent: float = 35) -> str:
    end = parse_date(end_date, date.today())
    start = parse_date(start_date, end - timedelta(days=30))
    rows = MetricService(db).high_acos_campaigns(start, end, store_name, Decimal(str(threshold_percent or 35)))
    if not rows:
        return f"没有发现 ACOS 高于 {threshold_percent:.2f}% 的广告活动。"
    lines = ["高 ACOS 广告活动："]
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. {row['campaignName']}（{row['channel']}）：花费 {row['spend']:,.2f}，"
            f"广告销售额 {row['sales']:,.2f}，ACOS {row['acos']:.2f}%，ROAS {row['roas']:.2f}"
        )
    lines.append("\n建议：先暂停或降价测试高 ACOS 活动，再检查关键词匹配、商品转化率和库存状态。")
    return "\n".join(lines)


def business_trend_chart(db: Session, months: int = 6, store_name: str | None = None, title: str | None = None) -> str:
    rows = MetricService(db).monthly_trend(months, store_name)
    option = {
        "title": {"text": title or "跨境经营趋势"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["净销售额", "利润"]},
        "xAxis": {"type": "category", "data": [r["month"] for r in rows]},
        "yAxis": {"type": "value", "name": "金额"},
        "series": [
            {"type": "line", "name": "净销售额", "smooth": True, "data": [float(r["netSales"]) for r in rows]},
            {"type": "line", "name": "利润", "smooth": True, "data": [float(r["profit"]) for r in rows]},
        ],
    }
    return "VISUAL_PAYLOAD:" + json.dumps({"kind": "echarts", "title": title, "option": option}, ensure_ascii=False)
