"""initial crossborder ops schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cb_store",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("marketplace", sa.String(length=40), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("manager_operator_id", sa.Integer(), nullable=True),
    )
    op.create_table(
        "cb_operator",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
    )
    op.create_table(
        "cb_sku",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("sku_code", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("target_marketplace", sa.String(length=40), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["cb_store.id"]),
    )
    op.create_table(
        "cb_order",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_no", sa.String(length=60), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("country", sa.String(length=40), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("cost_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("profit_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
    )
    op.create_table(
        "cb_refund",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("refund_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("refund_date", sa.Date(), nullable=False),
    )
    op.create_table(
        "cb_ad_campaign",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("campaign_name", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
    )
    op.create_table(
        "cb_ad_daily_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("spend", sa.Numeric(14, 2), nullable=False),
        sa.Column("sales_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("orders", sa.Integer(), nullable=False),
    )
    op.create_table(
        "cb_review",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=600), nullable=False),
        sa.Column("locale", sa.String(length=20), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=False),
    )
    op.create_table(
        "cb_listing",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("marketplace", sa.String(length=40), nullable=False),
        sa.Column("locale", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("bullets", sa.String(length=1200), nullable=False),
        sa.Column("keywords", sa.String(length=300), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_cb_order_store_date", "cb_order", ["store_id", "order_date"])
    op.create_index("ix_cb_refund_store_date", "cb_refund", ["store_id", "refund_date"])
    op.create_index("ix_cb_ad_report_store_date", "cb_ad_daily_report", ["store_id", "report_date"])


def downgrade() -> None:
    op.drop_index("ix_cb_ad_report_store_date", table_name="cb_ad_daily_report")
    op.drop_index("ix_cb_refund_store_date", table_name="cb_refund")
    op.drop_index("ix_cb_order_store_date", table_name="cb_order")
    op.drop_table("cb_listing")
    op.drop_table("cb_review")
    op.drop_table("cb_ad_daily_report")
    op.drop_table("cb_ad_campaign")
    op.drop_table("cb_refund")
    op.drop_table("cb_order")
    op.drop_table("cb_sku")
    op.drop_table("cb_operator")
    op.drop_table("cb_store")
