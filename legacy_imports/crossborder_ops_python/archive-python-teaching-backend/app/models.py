from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Store(Base):
    __tablename__ = "cb_store"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    platform: Mapped[str] = mapped_column(String(40))
    marketplace: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(10))
    manager_operator_id: Mapped[int | None]


class OperatorUser(Base):
    __tablename__ = "cb_operator"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    role: Mapped[str] = mapped_column(String(40))
    store_id: Mapped[int | None]
    email: Mapped[str | None] = mapped_column(String(120))


class SkuProduct(Base):
    __tablename__ = "cb_sku"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("cb_store.id"))
    sku_code: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60))
    target_marketplace: Mapped[str] = mapped_column(String(40))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(30))


class CommerceOrder(Base):
    __tablename__ = "cb_order"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(60))
    store_id: Mapped[int]
    sku_id: Mapped[int]
    country: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[int] = mapped_column(Integer)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    profit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(30))
    order_date: Mapped[date] = mapped_column(Date)


class RefundRecord(Base):
    __tablename__ = "cb_refund"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int]
    store_id: Mapped[int]
    sku_id: Mapped[int]
    reason: Mapped[str] = mapped_column(String(120))
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    refund_date: Mapped[date] = mapped_column(Date)


class AdCampaign(Base):
    __tablename__ = "cb_ad_campaign"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int]
    sku_id: Mapped[int]
    campaign_name: Mapped[str] = mapped_column(String(120))
    channel: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30))


class AdDailyReport(Base):
    __tablename__ = "cb_ad_daily_report"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int]
    store_id: Mapped[int]
    sku_id: Mapped[int]
    report_date: Mapped[date] = mapped_column(Date)
    spend: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    sales_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    clicks: Mapped[int] = mapped_column(Integer)
    orders: Mapped[int] = mapped_column(Integer)


class ProductReview(Base):
    __tablename__ = "cb_review"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int]
    sku_id: Mapped[int]
    rating: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(String(600))
    locale: Mapped[str] = mapped_column(String(20))
    review_date: Mapped[date] = mapped_column(Date)


class ProductListing(Base):
    __tablename__ = "cb_listing"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku_id: Mapped[int]
    marketplace: Mapped[str] = mapped_column(String(40))
    locale: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(220))
    bullets: Mapped[str] = mapped_column(String(1200))
    keywords: Mapped[str] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(DateTime)
