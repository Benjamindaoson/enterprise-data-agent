from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import DB_URL
from app.models import (
    AdCampaign,
    AdDailyReport,
    Base,
    CommerceOrder,
    OperatorUser,
    ProductListing,
    ProductReview,
    RefundRecord,
    SkuProduct,
    Store,
)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(Store.id).where(Store.id == 1)):
        return

    db.add_all([
        Store(id=1, name="Amazon US Store", platform="Amazon", marketplace="US", currency="USD", manager_operator_id=2),
        Store(id=2, name="Shopify DTC Store", platform="Shopify", marketplace="US", currency="USD", manager_operator_id=2),
        OperatorUser(id=1, name="Olivia Chen", role="OPERATOR", store_id=1, email="olivia@example.com"),
        OperatorUser(id=2, name="Mia Zhang", role="STORE_MANAGER", store_id=1, email="mia@example.com"),
        OperatorUser(id=3, name="Alex Wang", role="OPERATIONS_DIRECTOR", store_id=None, email="alex@example.com"),
        SkuProduct(id=1, store_id=1, sku_code="EB-US-1001", title="Wireless Earbuds", category="Electronics", target_marketplace="Amazon US", unit_cost=Decimal("18.50"), status="ACTIVE"),
        SkuProduct(id=2, store_id=1, sku_code="YM-US-2001", title="Yoga Mat", category="Sports", target_marketplace="Amazon US", unit_cost=Decimal("9.80"), status="ACTIVE"),
        SkuProduct(id=3, store_id=2, sku_code="BK-US-3001", title="Travel Backpack", category="Travel", target_marketplace="Shopify US", unit_cost=Decimal("21.20"), status="ACTIVE"),
    ])

    orders = [
        (1, "CB-202602-001", 1, 1, 120, "2800.00", "2400.00", "800.00", "1600.00", date(2026, 2, 12)),
        (2, "CB-202603-001", 1, 1, 260, "7600.00", "7200.00", "2300.00", "4900.00", date(2026, 3, 8)),
        (3, "CB-202604-001", 1, 2, 180, "5600.00", "5200.00", "1500.00", "3700.00", date(2026, 4, 18)),
        (4, "CB-202605-001", 1, 1, 420, "17200.00", "16800.00", "5900.00", "10900.00", date(2026, 5, 9)),
        (5, "CB-202606-001", 1, 2, 520, "37200.00", "36500.00", "12100.00", "24400.00", date(2026, 6, 6)),
        (6, "CB-202606-002", 2, 3, 170, "7200.00", "6500.00", "2500.00", "4000.00", date(2026, 6, 18)),
        (7, "CB-202607-001", 1, 1, 58, "3300.00", "2900.00", "1000.00", "1900.00", date(2026, 7, 1)),
        (8, "CB-202607-002", 2, 3, 42, "2600.00", "2400.00", "900.00", "1500.00", date(2026, 7, 3)),
    ]
    db.add_all([
        CommerceOrder(
            id=i, order_no=no, store_id=store_id, sku_id=sku_id, country="US", quantity=qty,
            gross_amount=Decimal(gross), net_amount=Decimal(net), cost_amount=Decimal(cost),
            profit_amount=Decimal(profit), status="COMPLETED", order_date=day,
        )
        for i, no, store_id, sku_id, qty, gross, net, cost, profit, day in orders
    ])

    db.add_all([
        RefundRecord(id=1, order_id=5, store_id=1, sku_id=2, reason="thin material", refund_amount=Decimal("465.00"), refund_date=date(2026, 6, 20)),
        RefundRecord(id=2, order_id=7, store_id=1, sku_id=1, reason="late delivery", refund_amount=Decimal("180.00"), refund_date=date(2026, 7, 2)),
        RefundRecord(id=3, order_id=8, store_id=2, sku_id=3, reason="zipper issue", refund_amount=Decimal("120.00"), refund_date=date(2026, 7, 4)),
        AdCampaign(id=1, store_id=1, sku_id=1, campaign_name="US Earbuds Prime Search", channel="Amazon Ads", status="ACTIVE"),
        AdCampaign(id=2, store_id=1, sku_id=2, campaign_name="Yoga Mat Broad Match", channel="Amazon Ads", status="ACTIVE"),
        AdDailyReport(id=1, campaign_id=1, store_id=1, sku_id=1, report_date=date(2026, 6, 15), spend=Decimal("1100.00"), sales_amount=Decimal("2600.00"), clicks=740, orders=36),
        AdDailyReport(id=2, campaign_id=2, store_id=1, sku_id=2, report_date=date(2026, 6, 16), spend=Decimal("820.00"), sales_amount=Decimal("1300.00"), clicks=430, orders=18),
        ProductReview(id=1, store_id=1, sku_id=2, rating=2, content="Too thin and smells like plastic", locale="en-US", review_date=date(2026, 6, 22)),
        ProductReview(id=2, store_id=1, sku_id=1, rating=3, content="Delivery was late but quality is fine", locale="en-US", review_date=date(2026, 7, 1)),
        ProductListing(id=1, sku_id=1, marketplace="Amazon US", locale="en-US", title="Wireless Earbuds", bullets="Long battery; Clear calls", keywords="earbuds, bluetooth", updated_at=datetime(2026, 6, 1, 0, 0, 0)),
    ])
    db.commit()


def main() -> None:
    engine = create_engine(DB_URL)
    init_db(engine)
    with Session(engine) as db:
        seed_demo_data(db)
    print("Database initialized and demo data seeded.")


if __name__ == "__main__":
    main()
