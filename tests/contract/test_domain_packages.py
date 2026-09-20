"""Tests for loading and validating business domain semantic packages."""

from __future__ import annotations

from pathlib import Path

import pytest

from eiw.semantic import (
    load_semantic_package_v2,
    get_package_domains,
    load_domain_package,
    SemanticPackageV2,
)


class TestPackageLoader:
    """Test semantic package loader functionality."""

    def test_get_package_domains(self) -> None:
        """Test getting list of available domains."""
        packages_dir = Path("semantic_packages")
        domains = get_package_domains(packages_dir)
        assert "finance" in domains
        assert "sales_operations" in domains
        assert "supply_chain" in domains

    def test_load_domain_package(self) -> None:
        """Test loading specific domain package."""
        packages_dir = Path("semantic_packages")
        package = load_domain_package(packages_dir, "finance")
        assert package.package.id == "finance"

    def test_load_nonexistent_domain_raises(self) -> None:
        """Test that loading nonexistent domain raises FileNotFoundError."""
        packages_dir = Path("semantic_packages")
        with pytest.raises(FileNotFoundError):
            load_domain_package(packages_dir, "nonexistent_domain")


class TestFinancePackage:
    """Test finance domain semantic package."""

    @pytest.fixture
    def finance_package(self) -> SemanticPackageV2:
        """Load finance domain package."""
        packages_dir = Path("semantic_packages")
        return load_domain_package(packages_dir, "finance")

    def test_finance_package_loads(self, finance_package: SemanticPackageV2) -> None:
        """Test that finance package loads successfully."""
        assert finance_package is not None
        assert finance_package.package.id == "finance"

    def test_finance_package_has_metrics(self, finance_package: SemanticPackageV2) -> None:
        """Test finance package has required metrics."""
        assert len(finance_package.metrics) >= 6

        metric_ids = [m.id for m in finance_package.metrics]
        assert "revenue" in metric_ids
        assert "gross_profit" in metric_ids
        assert "gross_margin_rate" in metric_ids
        assert "operating_expense" in metric_ids
        assert "operating_profit" in metric_ids
        assert "budget_variance" in metric_ids

    def test_finance_package_has_dimensions(self, finance_package: SemanticPackageV2) -> None:
        """Test finance package has required dimensions."""
        assert len(finance_package.dimensions) >= 5

        dimension_ids = [d.id for d in finance_package.dimensions]
        assert "region" in dimension_ids
        assert "product_category" in dimension_ids


class TestSalesOperationsPackage:
    """Test sales operations domain semantic package."""

    @pytest.fixture
    def sales_package(self) -> SemanticPackageV2:
        """Load sales operations domain package."""
        packages_dir = Path("semantic_packages")
        return load_domain_package(packages_dir, "sales_operations")

    def test_sales_package_loads(self, sales_package: SemanticPackageV2) -> None:
        """Test that sales operations package loads successfully."""
        assert sales_package is not None
        assert sales_package.package.id == "sales_operations"

    def test_sales_package_has_metrics(self, sales_package: SemanticPackageV2) -> None:
        """Test sales operations package has required metrics."""
        assert len(sales_package.metrics) >= 7

        metric_ids = [m.id for m in sales_package.metrics]
        assert "sales" in metric_ids
        assert "orders" in metric_ids


class TestSupplyChainPackage:
    """Test supply chain domain semantic package."""

    @pytest.fixture
    def supply_chain_package(self) -> SemanticPackageV2:
        """Load supply chain domain package."""
        packages_dir = Path("semantic_packages")
        return load_domain_package(packages_dir, "supply_chain")

    def test_supply_chain_package_loads(self, supply_chain_package: SemanticPackageV2) -> None:
        """Test that supply chain package loads successfully."""
        assert supply_chain_package is not None
        assert supply_chain_package.package.id == "supply_chain"

    def test_supply_chain_package_has_metrics(self, supply_chain_package: SemanticPackageV2) -> None:
        """Test supply chain package has required metrics."""
        assert len(supply_chain_package.metrics) >= 8

        metric_ids = [m.id for m in supply_chain_package.metrics]
        assert "inventory" in metric_ids
        assert "inventory_turnover" in metric_ids
        assert "stockout" in metric_ids
        assert "fill_rate" in metric_ids


class TestCrossDomainConsistency:
    """Test consistency across domain packages."""

    def test_shared_dimension_across_domains(self) -> None:
        """Test that shared dimensions exist across domains."""
        packages_dir = Path("semantic_packages")

        finance = load_domain_package(packages_dir, "finance")
        sales = load_domain_package(packages_dir, "sales_operations")

        # Product category should exist in both domains
        assert any(d.id == "product_category" for d in finance.dimensions)
        assert any(d.id == "product_category" for d in sales.dimensions)

        # Region should exist in both
        assert any(d.id == "region" for d in finance.dimensions)
        assert any(d.id == "region" for d in sales.dimensions)


class TestMetricValidation:
    """Test metric validation across domains."""

    def test_finance_metric_validation(self) -> None:
        """Test validation of finance metrics."""
        packages_dir = Path("semantic_packages")
        package = load_domain_package(packages_dir, "finance")

        # Valid reference
        is_valid, issues = package.validate_metric_reference(
            metric_id="revenue",
            dimension_ids=["region"],
        )
        assert is_valid

        # Invalid metric
        is_valid, issues = package.validate_metric_reference(
            metric_id="nonexistent",
            dimension_ids=["region"],
        )
        assert not is_valid
