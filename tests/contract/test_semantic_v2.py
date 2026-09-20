"""Tests for Semantic Layer v2 validation and schema enforcement."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from eiw.semantic import (
    SemanticPackageV2,
    MetricDefinition,
    DimensionDefinition,
    TimeGrain,
    AggregationType,
    SemanticType,
    DataClassification,
    Availability,
    Freshness,
)


def make_metric_dict(
    metric_id: str = "test_metric",
    name: str = "Test Metric",
    version: str = "1.0.0",
    **overrides,
) -> dict:
    """Create a valid metric dict with required fields."""
    metric = {
        "id": metric_id,
        "version": version,
        "name": name,
        "description": "A test metric",
        "formula": {
            "type": "aggregation",
            "expression": "SUM(amount)",
            "source_table": "public.sales",
            "required_dimensions": ["region"],
        },
        "unit": "USD",
        "aggregation": "SUM",
        "semantic_type": "NUMERIC",
        "supported_grains": [{"grain": "DAILY", "available": True}],
        "default_grain": "DAILY",
        "required_dimensions": ["region"],
        "source_table": "public.sales",
        "availability": {"from": "2020-01-01", "to": "2100-12-31"},
        "owner": "test_team",
    }
    metric.update(overrides)
    return metric


def make_dimension_dict(
    dim_id: str = "region",
    name: str = "Region",
    **overrides,
) -> dict:
    """Create a valid dimension dict with required fields."""
    dim = {
        "id": dim_id,
        "name": name,
        "source_table": "public.regions",
        "source_column": "region_id",
    }
    dim.update(overrides)
    return dim


def make_package_dict(
    package_id: str = "test_domain",
    version: str = "1.0.0",
    **overrides,
) -> dict:
    """Create a valid package identity dict."""
    pkg = {
        "id": package_id,
        "version": version,
        "title": "Test Domain",
        "domain": "test",
        "source_snapshot_alias": "latest",
        "default_snapshot": "snap_001",
    }
    pkg.update(overrides)
    return pkg


class TestSemanticSchemaValidation:
    """Test semantic package schema validation."""

    def test_valid_minimal_metric(self) -> None:
        """Test creating a minimal valid metric."""
        metric_dict = make_metric_dict()
        metric = MetricDefinition.model_validate(metric_dict)
        assert metric.id == "test_metric"
        assert metric.name == "Test Metric"
        assert metric.aggregation == AggregationType.SUM

    def test_valid_full_metric(self) -> None:
        """Test creating a metric with all fields."""
        metric_dict = make_metric_dict(
            metric_id="revenue",
            name="Total Revenue",
            unit="USD",
            aliases=["total_revenue", "sales_revenue"],
            supported_grains=[
                {"grain": "DAILY", "available": True},
                {"grain": "MONTHLY", "available": True},
            ],
            default_grain="MONTHLY",
            required_dimensions=["region", "product"],
        )
        metric = MetricDefinition.model_validate(metric_dict)
        assert metric.formula.expression == "SUM(amount)"
        assert "total_revenue" in metric.aliases

    def test_invalid_metric_missing_required_fields(self) -> None:
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricDefinition.model_validate({
                "id": "",  # Empty ID should fail
                "name": "Test",
                "formula": {
                    "type": "aggregation",
                    "expression": "SUM(amount)",
                    "source_table": "public.sales",
                },
                "unit": "USD",
                "aggregation": "SUM",
                "semantic_type": "NUMERIC",
                "supported_grains": [{"grain": "DAILY", "available": True}],
                "default_grain": "DAILY",
                "required_dimensions": ["region"],
                "source_table": "public.sales",
                "availability": {"from_date": "2020-01-01", "to_date": "2100-12-31"},
                "owner": "test",
            })
        assert "id" in str(exc_info.value)

    def test_invalid_metric_bad_aggregation(self) -> None:
        """Test that invalid aggregation type raises error."""
        with pytest.raises(ValidationError):
            MetricDefinition.model_validate(make_metric_dict(aggregation="invalid_agg"))

    def test_valid_dimension(self) -> None:
        """Test creating a valid dimension."""
        dimension = DimensionDefinition.model_validate(make_dimension_dict(
            dim_id="region",
            name="Region",
            description="Sales region",
            aliases=["territory", "area"],
            cardinality="medium",
        ))
        assert dimension.id == "region"

    def test_dimension_with_policy_tags(self) -> None:
        """Test dimension with policy tags."""
        dimension = DimensionDefinition.model_validate(make_dimension_dict(
            dim_id="customer",
            name="Customer",
            policy_tags=["PII", "RESTRICTED"],
        ))
        assert "PII" in dimension.policy_tags

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields not in schema raise ValidationError."""
        with pytest.raises(ValidationError):
            MetricDefinition.model_validate(make_metric_dict(unknown_field="should_fail"))

    def test_version_in_package_metrics(self) -> None:
        """Test that package version propagates to components."""
        package = SemanticPackageV2(
            package=make_package_dict(
                package_id="test_domain",
                version="2.0.0",
            ),
            metrics=[
                make_metric_dict(
                    metric_id="metric1",
                    version="1.0.0",
                ),
            ],
            dimensions=[
                make_dimension_dict(dim_id="dim1", name="Dimension 1"),
            ],
        )
        assert package.package.version == "2.0.0"
        assert package.metrics[0].version == "1.0.0"


class TestMetricReferenceValidation:
    """Test metric reference validation."""

    @pytest.fixture
    def sample_package(self) -> SemanticPackageV2:
        """Create a sample package for testing."""
        return SemanticPackageV2(
            package=make_package_dict(package_id="test_domain"),
            metrics=[
                make_metric_dict(
                    metric_id="revenue",
                    name="Revenue",
                    required_dimensions=["region", "product"],
                ),
            ],
            dimensions=[
                make_dimension_dict(dim_id="region", name="Region"),
                make_dimension_dict(dim_id="product", name="Product"),
            ],
        )

    def test_valid_metric_reference(self, sample_package: SemanticPackageV2) -> None:
        """Test valid metric reference passes validation."""
        is_valid, issues = sample_package.validate_metric_reference(
            metric_id="revenue",
            dimension_ids=["region", "product"],
        )
        assert is_valid
        assert len(issues) == 0

    def test_invalid_metric_reference(self, sample_package: SemanticPackageV2) -> None:
        """Test invalid metric reference fails validation."""
        is_valid, issues = sample_package.validate_metric_reference(
            metric_id="nonexistent_metric",
            dimension_ids=["region"],
        )
        assert not is_valid
        assert len(issues) > 0

    def test_date_range_validation(self, sample_package: SemanticPackageV2) -> None:
        """Test that date range outside availability fails."""
        # The sample package has availability from 2020-01-01 to 2100-12-31
        # Query before that range should fail
        is_valid, issues = sample_package.validate_metric_reference(
            metric_id="revenue",
            dimension_ids=["region", "product"],
            start_date=date(1990, 1, 1),
            end_date=date(1990, 12, 31),
        )
        assert not is_valid
        assert any("not available" in issue.lower() for issue in issues)


class TestAliasResolution:
    """Test metric and dimension alias resolution."""

    @pytest.fixture
    def package_with_aliases(self) -> SemanticPackageV2:
        """Create package with various aliases."""
        return SemanticPackageV2(
            package=make_package_dict(package_id="finance"),
            metrics=[
                make_metric_dict(
                    metric_id="gross_profit",
                    name="Gross Profit",
                    aliases=["profit", "gross_margin", "GP"],
                    formula={
                        "type": "aggregation",
                        "expression": "SUM(revenue) - SUM(cogs)",
                        "source_table": "public.financials",
                        "required_dimensions": ["region"],
                    },
                    source_table="public.financials",
                ),
            ],
            dimensions=[
                make_dimension_dict(
                    dim_id="fiscal_period",
                    name="Fiscal Period",
                    aliases=["period", "fp", "fiscal"],
                ),
            ],
        )

    def test_resolve_metric_by_alias(self, package_with_aliases: SemanticPackageV2) -> None:
        """Test resolving metric by alias."""
        metric = package_with_aliases.find_metric_by_alias("profit")
        assert metric is not None
        assert metric.id == "gross_profit"

    def test_resolve_metric_by_id(self, package_with_aliases: SemanticPackageV2) -> None:
        """Test resolving metric by ID."""
        metric = package_with_aliases.metric("gross_profit")
        assert metric is not None
        assert metric.id == "gross_profit"

    def test_resolve_dimension_by_alias(self, package_with_aliases: SemanticPackageV2) -> None:
        """Test resolving dimension by alias."""
        dimension = package_with_aliases.find_dimension_by_alias("fp")
        assert dimension is not None
        assert dimension.id == "fiscal_period"

    def test_alias_not_found(self, package_with_aliases: SemanticPackageV2) -> None:
        """Test that non-existent alias returns None."""
        metric = package_with_aliases.find_metric_by_alias("nonexistent_alias")
        assert metric is None

    def test_case_insensitive_alias_resolution(self, package_with_aliases: SemanticPackageV2) -> None:
        """Test that alias resolution is case-insensitive."""
        metric = package_with_aliases.find_metric_by_alias("PROFIT")
        assert metric is not None
        assert metric.id == "gross_profit"


class TestVersionPropagation:
    """Test version propagation through semantic package."""

    def test_package_version_preserved(self) -> None:
        """Test that package version is preserved."""
        package = SemanticPackageV2(
            package=make_package_dict(
                package_id="sales",
                version="3.0.0",
            ),
            metrics=[
                make_metric_dict(
                    metric_id="sales",
                    name="Sales Amount",
                    version="1.5.0",
                ),
            ],
            dimensions=[
                make_dimension_dict(dim_id="region", name="Region"),
            ],
        )
        assert package.package.version == "3.0.0"
        assert package.metrics[0].version == "1.5.0"


class TestAvailabilityValidation:
    """Test availability validation."""

    def test_availability_date_order(self) -> None:
        """Test that to_date must be after from_date."""
        with pytest.raises(ValidationError):
            Availability.model_validate({
                "from": "2023-12-31",
                "to": "2023-01-01",
            })

    def test_availability_valid(self) -> None:
        """Test valid availability."""
        avail = Availability.model_validate({
            "from": "2023-01-01",
            "to": "2023-12-31",
        })
        assert avail.from_date == date(2023, 1, 1)
        assert avail.to_date == date(2023, 12, 31)

    def test_availability_covers(self) -> None:
        """Test availability covers method."""
        avail = Availability.model_validate({
            "from": "2023-01-01",
            "to": "2023-12-31",
        })
        assert avail.covers(date(2023, 6, 1), date(2023, 6, 30))
        assert not avail.covers(date(2022, 6, 1), date(2022, 6, 30))
        assert avail.covers(None, None)  # No date specified means covers all
