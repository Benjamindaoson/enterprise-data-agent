"""Period Comparison Analysis for Enterprise Data Agent.

Compares metrics across time periods:
- Period-over-period analysis
- YoY (Year-over-Year) comparison
- MoM (Month-over-Month) comparison
- WoW (Week-over-Week) comparison
- Custom period comparison
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ComparisonPeriod(Enum):
    """Type of period comparison."""

    YOY = "year_over_year"
    MOM = "month_over_month"
    WOW = "week_over_week"
    QOQ = "quarter_over_quarter"
    CUSTOM = "custom"


from enum import Enum


@dataclass
class PeriodComparison:
    """Comparison between two periods."""

    period_name: str
    start_date: str
    end_date: str
    value: float
    comparison_value: float
    absolute_change: float
    percentage_change: float
    contribution_to_total: float


@dataclass
class PeriodComparisonResult:
    """Result of period comparison analysis."""

    metric_id: str
    comparison_type: ComparisonPeriod
    comparisons: list[PeriodComparison] = field(default_factory=list)
    overall_change: float
    overall_percentage_change: float
    trend: str  # improving, declining, stable
    summary: str


class PeriodComparator:
    """Compares metrics across time periods.

    This comparator provides:
    1. Period-over-period comparisons
    2. Year-over-Year analysis
    3. Seasonality-aware comparisons
    4. Multiple period comparison
    """

    def __init__(self) -> None:
        """Initialize period comparator."""
        pass

    def compare_yoy(
        self,
        current_data: list[dict[str, Any]],
        previous_data: list[dict[str, Any]],
        metric_id: str,
    ) -> PeriodComparisonResult:
        """Compare current year to previous year.

        Args:
            current_data: Current period data
            previous_data: Previous period data
            metric_id: Metric being compared

        Returns:
            Period comparison result
        """
        current_value = self._sum_values(current_data)
        previous_value = self._sum_values(previous_data)

        change = current_value - previous_value
        pct_change = (change / previous_value * 100) if previous_value != 0 else 0

        comparison = PeriodComparison(
            period_name="Year-over-Year",
            start_date="Current Year",
            end_date="Previous Year",
            value=current_value,
            comparison_value=previous_value,
            absolute_change=change,
            percentage_change=pct_change,
            contribution_to_total=100,
        )

        return PeriodComparisonResult(
            metric_id=metric_id,
            comparison_type=ComparisonPeriod.YOY,
            comparisons=[comparison],
            overall_change=change,
            overall_percentage_change=pct_change,
            trend=self._classify_trend(pct_change),
            summary=self._generate_summary("Year-over-Year", current_value, previous_value, pct_change),
        )

    def compare_mom(
        self,
        current_month: list[dict[str, Any]],
        previous_month: list[dict[str, Any]],
        metric_id: str,
    ) -> PeriodComparisonResult:
        """Compare current month to previous month."""
        current_value = self._sum_values(current_month)
        previous_value = self._sum_values(previous_month)

        change = current_value - previous_value
        pct_change = (change / previous_value * 100) if previous_value != 0 else 0

        comparison = PeriodComparison(
            period_name="Month-over-Month",
            start_date="Current Month",
            end_date="Previous Month",
            value=current_value,
            comparison_value=previous_value,
            absolute_change=change,
            percentage_change=pct_change,
            contribution_to_total=100,
        )

        return PeriodComparisonResult(
            metric_id=metric_id,
            comparison_type=ComparisonPeriod.MOM,
            comparisons=[comparison],
            overall_change=change,
            overall_percentage_change=pct_change,
            trend=self._classify_trend(pct_change),
            summary=self._generate_summary("Month-over-Month", current_value, previous_value, pct_change),
        )

    def compare_multiple_periods(
        self,
        periods: list[dict[str, Any]],  # Each with: name, data
        metric_id: str,
    ) -> PeriodComparisonResult:
        """Compare multiple periods.

        Args:
            periods: List of period dicts with 'name' and 'data'
            metric_id: Metric being compared

        Returns:
            Period comparison result
        """
        comparisons = []
        overall_change = 0.0
        overall_pct_change = 0.0

        for i, period in enumerate(periods):
            current_value = self._sum_values(period.get("data", []))
            current_name = period.get("name", f"Period {i + 1}")

            if i == 0:
                comparison = PeriodComparison(
                    period_name=current_name,
                    start_date="N/A",
                    end_date="N/A",
                    value=current_value,
                    comparison_value=0,
                    absolute_change=0,
                    percentage_change=0,
                    contribution_to_total=100,
                )
            else:
                prev_value = self._sum_values(periods[i - 1].get("data", []))
                change = current_value - prev_value
                pct_change = (change / prev_value * 100) if prev_value != 0 else 0

                comparison = PeriodComparison(
                    period_name=current_name,
                    start_date=periods[i - 1].get("name", "Previous"),
                    end_date=current_name,
                    value=current_value,
                    comparison_value=prev_value,
                    absolute_change=change,
                    percentage_change=pct_change,
                    contribution_to_total=0,  # Calculate relative to first period
                )

            comparisons.append(comparison)

        # Calculate overall change from first to last
        if len(periods) >= 2:
            first_value = self._sum_values(periods[0].get("data", []))
            last_value = self._sum_values(periods[-1].get("data", []))
            overall_change = last_value - first_value
            overall_pct_change = (overall_change / first_value * 100) if first_value != 0 else 0

        return PeriodComparisonResult(
            metric_id=metric_id,
            comparison_type=ComparisonPeriod.CUSTOM,
            comparisons=comparisons,
            overall_change=overall_change,
            overall_percentage_change=overall_pct_change,
            trend=self._classify_trend(overall_pct_change),
            summary=f"Compared {len(periods)} periods. Overall change: {overall_pct_change:.1f}%",
        )

    def _sum_values(self, data: list[dict[str, Any]]) -> float:
        """Sum values in data."""
        if not data:
            return 0.0
        return sum(d.get("value", 0) for d in data)

    def _classify_trend(self, pct_change: float) -> str:
        """Classify trend based on percentage change."""
        if pct_change > 5:
            return "improving"
        elif pct_change < -5:
            return "declining"
        else:
            return "stable"

    def _generate_summary(
        self,
        period_type: str,
        current: float,
        previous: float,
        pct_change: float,
    ) -> str:
        """Generate comparison summary."""
        direction = "increased" if pct_change > 0 else "decreased"

        return (
            f"{period_type} comparison: "
            f"Current value {current:.2f} vs Previous {previous:.2f}. "
            f"Change: {direction} by {abs(pct_change):.1f}%"
        )
