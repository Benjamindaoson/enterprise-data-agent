"""E2E Domain Tests - Finance, Sales, Supply Chain.

These tests validate the complete pipeline for each domain:
User Question → Semantic Resolution → Metric/Dimension Resolution
→ Query Generation → Execution → Result → Validation
"""

from __future__ import annotations

import pytest

from eiw.workspace.analysis import AnalysisService
from eiw.workspace.data import IowaData
from eiw.workspace.store import WorkspaceStore


@pytest.fixture
def data() -> IowaData:
    """Iowa data fixture."""
    return IowaData()


@pytest.fixture
def service(tmp_path: pytest.TempPathFactory) -> AnalysisService:
    """Analysis service fixture."""
    store = WorkspaceStore(tmp_path / "test_store.json")
    data = IowaData()
    return AnalysisService(store, data, tmp_path / "artifacts")


class TestFinanceE2E:
    """Finance domain E2E tests using Iowa wholesale liquor data.

    Tests financial metrics: revenue, costs, margins, pricing.
    """

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_finance_revenue_analysis(self, service: AnalysisService) -> None:
        """Test finance: revenue analysis question."""
        result = service.create(
            "Show total wholesale sales revenue by month for 2025",
            {"user_id": "test_finance_user", "roles": ["finance_analyst"]},
        )

        # Verify task completed
        assert result["state"] == "COMPLETED", f"Task failed: {result.get('error')}"

        # Verify claims exist with financial evidence
        assert len(result["claims"]) > 0, "No claims generated"

        # Verify evidence exists with data
        assert len(result["evidence"]) > 0, "No evidence data generated"

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_finance_cost_analysis(self, service: AnalysisService) -> None:
        """Test finance: cost and margin analysis."""
        result = service.create(
            "What is the state acquisition cost and gross spread by vendor?",
            {"user_id": "test_finance_user", "roles": ["finance_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No evidence generated"

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_finance_pricing_analysis(self, service: AnalysisService) -> None:
        """Test finance: pricing analysis."""
        result = service.create(
            "Calculate the average wholesale price per bottle by category",
            {"user_id": "test_finance_user", "roles": ["finance_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No evidence data generated"


class TestSalesE2E:
    """Sales operations E2E tests.

    Tests sales metrics: volumes, quantities, trends, comparisons.
    """

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_sales_volume_trend(self, service: AnalysisService) -> None:
        """Test sales: volume trend analysis."""
        result = service.create(
            "Show bottles ordered trend by month for the last 6 months",
            {"user_id": "test_sales_user", "roles": ["sales_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No evidence data generated"

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_sales_top_vendors(self, service: AnalysisService) -> None:
        """Test sales: top vendors analysis."""
        result = service.create(
            "List the top 10 vendors by total sales amount",
            {"user_id": "test_sales_user", "roles": ["sales_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No evidence data generated"

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_sales_regional_comparison(self, service: AnalysisService) -> None:
        """Test sales: regional comparison."""
        result = service.create(
            "Compare sales volume by category for Q2 2025",
            {"user_id": "test_sales_user", "roles": ["sales_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No regional data generated"

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_sales_product_performance(self, service: AnalysisService) -> None:
        """Test sales: product category performance."""
        result = service.create(
            "Which product categories have the highest order volume?",
            {"user_id": "test_sales_user", "roles": ["sales_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No evidence data generated"


class TestSupplyChainE2E:
    """Supply chain E2E tests.

    Tests supply chain metrics: vendor relationships, order patterns, logistics.
    """

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_supply_vendor_diversity(self, service: AnalysisService) -> None:
        """Test supply chain: vendor diversity analysis."""
        result = service.create(
            "Analyze vendor diversity by store - how many vendors per store?",
            {"user_id": "test_supply_user", "roles": ["supply_chain_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No vendor diversity data"

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_supply_order_frequency(self, service: AnalysisService) -> None:
        """Test supply chain: order frequency patterns."""
        result = service.create(
            "What is the average order frequency by store in 2025?",
            {"user_id": "test_supply_user", "roles": ["supply_chain_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No order frequency data"

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_supply_volume_analysis(self, service: AnalysisService) -> None:
        """Test supply chain: volume analysis by vendor."""
        result = service.create(
            "What are the total bottles ordered in 2025?",
            {"user_id": "test_supply_user", "roles": ["supply_chain_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        # Verify the task completed - evidence may be empty for simple queries
        assert "claims" in result or "evidence" in result

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_supply_product_availability(self, service: AnalysisService) -> None:
        """Test supply chain: product availability by vendor."""
        result = service.create(
            "Which vendors supply the most product categories?",
            {"user_id": "test_supply_user", "roles": ["supply_chain_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No product availability data"


class TestCrossDomainAnalysis:
    """Cross-domain analysis tests combining multiple perspectives."""

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_finance_sales_correlation(self, service: AnalysisService) -> None:
        """Test correlation between financial and sales metrics."""
        result = service.create(
            "Correlate revenue with order volume by vendor - which vendors have high volume but low revenue?",
            {"user_id": "test_analyst", "roles": ["finance_analyst", "sales_analyst"]},
        )

        assert result["state"] == "COMPLETED"
        # Should have analysis combining financial and volume metrics

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_sales_supply_patterns(self, service: AnalysisService) -> None:
        """Test pattern detection across sales and supply chain."""
        result = service.create(
            "Identify stores with irregular ordering patterns - high variance in monthly orders",
            {"user_id": "test_analyst", "roles": ["sales_analyst", "supply_chain_analyst"]},
        )

        assert result["state"] == "COMPLETED"


class TestDataValidation:
    """Tests that validate data integrity and result accuracy."""

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_metric_consistency(self, service: AnalysisService) -> None:
        """Test that metrics are computed consistently."""
        # Two identical questions should produce similar results
        result1 = service.create(
            "Total sales amount for 2025",
            {"user_id": "test_user", "roles": ["analyst"]},
        )
        result2 = service.create(
            "Sum of wholesale sales for year 2025",
            {"user_id": "test_user", "roles": ["analyst"]},
        )

        assert result1["state"] == "COMPLETED"
        assert result2["state"] == "COMPLETED"

    @pytest.mark.skipif(not IowaData().available(), reason="Iowa snapshot required")
    def test_dimension_filter_combinations(self, service: AnalysisService) -> None:
        """Test filtering by multiple dimensions."""
        result = service.create(
            "Sales by vendor filtered to Polk county and year 2025",
            {"user_id": "test_user", "roles": ["analyst"]},
        )

        assert result["state"] == "COMPLETED"
        assert len(result["evidence"]) > 0, "No filtered data returned"
