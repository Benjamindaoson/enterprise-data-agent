from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, AdCampaign, AdDailyReport, CommerceOrder, RefundRecord, SkuProduct, Store
from app.tools import business_trend_chart, high_acos_campaigns, refund_risks, summarize_business


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    db = Session()
    db.add_all([
        Store(id=1, name="Amazon US Store", platform="Amazon", marketplace="US", currency="USD", manager_operator_id=2),
        SkuProduct(id=1, store_id=1, sku_code="EB-US-1001", title="Wireless Earbuds", category="Electronics", target_marketplace="Amazon US", unit_cost=Decimal("18.50"), status="ACTIVE"),
        SkuProduct(id=2, store_id=1, sku_code="YM-US-2001", title="Yoga Mat", category="Sports", target_marketplace="Amazon US", unit_cost=Decimal("9.80"), status="ACTIVE"),
        CommerceOrder(id=1, order_no="CB-1", store_id=1, sku_id=1, country="US", quantity=10, gross_amount=Decimal("1000"), net_amount=Decimal("900"), cost_amount=Decimal("300"), profit_amount=Decimal("600"), status="COMPLETED", order_date=date(2026, 6, 10)),
        CommerceOrder(id=2, order_no="CB-2", store_id=1, sku_id=2, country="US", quantity=5, gross_amount=Decimal("500"), net_amount=Decimal("400"), cost_amount=Decimal("100"), profit_amount=Decimal("300"), status="COMPLETED", order_date=date(2026, 6, 11)),
        RefundRecord(id=1, order_id=2, store_id=1, sku_id=2, reason="thin", refund_amount=Decimal("79"), refund_date=date(2026, 6, 12)),
        AdCampaign(id=1, store_id=1, sku_id=1, campaign_name="US Earbuds Prime Search", channel="Amazon Ads", status="ACTIVE"),
        AdDailyReport(id=1, campaign_id=1, store_id=1, sku_id=1, report_date=date(2026, 6, 13), spend=Decimal("450"), sales_amount=Decimal("900"), clicks=100, orders=10),
    ])
    db.commit()
    return db


def test_business_summary_includes_average_order_profit():
    text = summarize_business(make_session(), "2026-06-01", "2026-06-30")

    assert "平均订单利润" in text
    assert "450.00" in text


def test_refund_risk_uses_seeded_refund_data():
    text = refund_risks(make_session(), "2026-06-01", "2026-06-30")

    assert "退款风险 SKU 排名" in text
    assert "YM-US-2001" in text


def test_ad_tool_returns_acos_and_roas():
    text = high_acos_campaigns(make_session(), "2026-06-01", "2026-06-30", threshold_percent=35)

    assert "US Earbuds Prime Search" in text
    assert "ACOS 50.00%" in text
    assert "ROAS 2.00" in text


def test_chart_payload_is_echarts_payload():
    text = business_trend_chart(make_session(), 6, title="测试趋势图")

    assert text.startswith("VISUAL_PAYLOAD:")
    assert '"kind": "echarts"' in text
    assert '"series"' in text
