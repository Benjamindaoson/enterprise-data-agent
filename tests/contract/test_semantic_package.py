from datetime import date
from pathlib import Path

import pytest

from eiw.semantic.package import load_semantic_package

PACKAGE_PATH = Path("semantic_packages/iowa_liquor_wholesale/semantic-package.yaml")


def test_semantic_package_has_the_frozen_metric_and_dimension_surface() -> None:
    package = load_semantic_package(PACKAGE_PATH)
    assert package.package.id == "iowa_liquor_wholesale"
    assert {metric.id for metric in package.metrics} == {
        "wholesale_sales_amount",
        "bottles_ordered",
        "volume_liters",
        "average_wholesale_price_per_bottle",
        "state_acquisition_cost",
        "wholesale_gross_spread",
        "wholesale_spread_rate",
        "average_state_cost_per_bottle",
    }
    assert {dimension.id for dimension in package.dimensions} >= {
        "store",
        "county",
        "vendor",
        "product",
    }


def test_cost_metrics_do_not_cover_pre_july_2025_data() -> None:
    package = load_semantic_package(PACKAGE_PATH)
    spread = package.metric("wholesale_gross_spread")
    assert not spread.covers(date(2024, 3, 1), date(2024, 3, 31))
    assert spread.covers(date(2026, 6, 1), date(2026, 7, 31))
    assert spread.unavailable_behavior == "reject_or_partial_never_zero_fill"


def test_event_time_history_is_authoritative() -> None:
    package = load_semantic_package(PACKAGE_PATH)
    policies = {policy["id"]: policy for policy in package.join_policies}
    assert policies["fact_to_store_current"]["historical_authority"] == "fact_wins"
    assert policies["fact_to_product_current"]["historical_authority"] == "fact_wins"


def test_unknown_metric_is_rejected() -> None:
    package = load_semantic_package(PACKAGE_PATH)
    with pytest.raises(KeyError, match="unknown metric"):
        package.metric("gross_profit")
