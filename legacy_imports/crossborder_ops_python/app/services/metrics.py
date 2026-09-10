from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AdCampaign, AdDailyReport, CommerceOrder, RefundRecord, SkuProduct, Store

ZERO = Decimal("0.00")


def money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return ZERO
    return (numerator * Decimal("100") / denominator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class BusinessSummary:
    store_name: str
    start_date: date
    end_date: date
    net_sales: Decimal
    profit: Decimal
    profit_rate: Decimal
    average_order_profit: Decimal
    refund_amount: Decimal
    refund_rate: Decimal
    units: int
    orders: int


class MetricService:
    def __init__(self, db: Session):
        self.db = db

    def store_id(self, store_name: str | None) -> int | None:
        if not store_name:
            return None
        return self.db.scalar(select(Store.id).where(Store.name.ilike(f"%{store_name.strip()}%")))

    def store_name(self, store_id: int | None) -> str:
        if store_id is None:
            return "全部店铺"
        return self.db.scalar(select(Store.name).where(Store.id == store_id)) or "未知店铺"

    def summarize_business(self, start: date, end: date, store_name: str | None = None) -> BusinessSummary:
        store_id = self.store_id(store_name)
        filters = [CommerceOrder.order_date.between(start, end)]
        if store_id is not None:
            filters.append(CommerceOrder.store_id == store_id)
        row = self.db.execute(
            select(
                func.coalesce(func.sum(CommerceOrder.net_amount), 0),
                func.coalesce(func.sum(CommerceOrder.profit_amount), 0),
                func.coalesce(func.sum(CommerceOrder.quantity), 0),
                func.count(CommerceOrder.id),
            ).where(*filters)
        ).one()
        net_sales, profit, units, orders = money(row[0]), money(row[1]), int(row[2] or 0), int(row[3] or 0)
        refund_filters = [RefundRecord.refund_date.between(start, end)]
        if store_id is not None:
            refund_filters.append(RefundRecord.store_id == store_id)
        refund_amount = money(self.db.scalar(select(func.coalesce(func.sum(RefundRecord.refund_amount), 0)).where(*refund_filters)))
        avg_profit = ZERO if orders == 0 else money(profit / Decimal(orders))
        return BusinessSummary(
            self.store_name(store_id), start, end, net_sales, profit,
            percent(profit, net_sales), avg_profit, refund_amount,
            percent(refund_amount, net_sales), units, orders,
        )

    def monthly_trend(self, months: int, store_name: str | None = None) -> list[dict]:
        store_id = self.store_id(store_name)
        rows = self.db.scalars(select(CommerceOrder).order_by(CommerceOrder.order_date)).all()
        if store_id is not None:
            rows = [r for r in rows if r.store_id == store_id]
        buckets: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"netSales": ZERO, "profit": ZERO})
        for row in rows:
            key = row.order_date.strftime("%Y-%m")
            buckets[key]["netSales"] += money(row.net_amount)
            buckets[key]["profit"] += money(row.profit_amount)
        return [{"month": k, **v} for k, v in sorted(buckets.items())[-max(1, min(months or 6, 18)):]]

    def refund_risks(self, start: date, end: date, store_name: str | None = None, top_n: int = 5) -> list[dict]:
        store_id = self.store_id(store_name)
        order_filters = [CommerceOrder.order_date.between(start, end)]
        refund_filters = [RefundRecord.refund_date.between(start, end)]
        if store_id is not None:
            order_filters.append(CommerceOrder.store_id == store_id)
            refund_filters.append(RefundRecord.store_id == store_id)
        units = dict(self.db.execute(select(CommerceOrder.sku_id, func.coalesce(func.sum(CommerceOrder.quantity), 0)).where(*order_filters).group_by(CommerceOrder.sku_id)).all())
        refunds = self.db.scalars(select(RefundRecord).where(*refund_filters)).all()
        amount_by_sku: dict[int, Decimal] = defaultdict(lambda: ZERO)
        count_by_sku: dict[int, int] = defaultdict(int)
        for row in refunds:
            amount_by_sku[row.sku_id] += money(row.refund_amount)
            count_by_sku[row.sku_id] += 1
        sku_map = {s.id: s for s in self.db.scalars(select(SkuProduct)).all()}
        result = []
        for sku_id, amount in amount_by_sku.items():
            sku = sku_map.get(sku_id)
            sold_units = max(int(units.get(sku_id, 0) or 0), 1)
            result.append({
                "skuCode": sku.sku_code if sku else "UNKNOWN",
                "title": sku.title if sku else "Unknown SKU",
                "refunds": count_by_sku[sku_id],
                "units": sold_units,
                "refundRate": percent(Decimal(count_by_sku[sku_id]), Decimal(sold_units)),
                "refundAmount": money(amount),
            })
        return sorted(result, key=lambda r: r["refundRate"], reverse=True)[:max(1, min(top_n or 5, 20))]

    def high_acos_campaigns(self, start: date, end: date, store_name: str | None = None, threshold: Decimal = Decimal("35")) -> list[dict]:
        store_id = self.store_id(store_name)
        filters = [AdDailyReport.report_date.between(start, end)]
        if store_id is not None:
            filters.append(AdDailyReport.store_id == store_id)
        rows = self.db.scalars(select(AdDailyReport).where(*filters)).all()
        campaigns = {c.id: c for c in self.db.scalars(select(AdCampaign)).all()}
        grouped: dict[int, dict[str, Decimal]] = defaultdict(lambda: {"spend": ZERO, "sales": ZERO})
        for row in rows:
            grouped[row.campaign_id]["spend"] += money(row.spend)
            grouped[row.campaign_id]["sales"] += money(row.sales_amount)
        result = []
        for campaign_id, values in grouped.items():
            acos = percent(values["spend"], values["sales"])
            if acos < threshold:
                continue
            campaign = campaigns.get(campaign_id)
            spend = values["spend"]
            roas = ZERO if spend == 0 else money(values["sales"] / max(spend, Decimal("1")))
            result.append({
                "campaignName": campaign.campaign_name if campaign else "Unknown Campaign",
                "channel": campaign.channel if campaign else "Unknown",
                "spend": spend,
                "sales": values["sales"],
                "acos": acos,
                "roas": roas,
            })
        return sorted(result, key=lambda r: r["acos"], reverse=True)
