"""Contribution Analysis for Enterprise Data Agent.

Analyzes contribution of different segments to a total:
- Absolute contribution
- Percentage contribution
- Contribution to change
- Contribution variance analysis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Contribution:
    """Contribution of a segment."""

    segment_name: str
    segment_value: float
    total_value: float
    percentage: float  # 0-100
    contribution_type: str  # absolute, change, variance


@dataclass
class ContributionAnalysisResult:
    """Result of contribution analysis."""

    metric_id: str
    total_value: float
    contributions: list[Contribution] = field(default_factory=list)
    top_contributor: str | None = None
    analysis_type: str = "absolute"


class ContributionAnalyzer:
    """Analyzes contribution of segments to totals.

    Provides:
    1. Absolute contribution analysis
    2. Percentage contribution analysis
    3. Contribution to change (delta analysis)
    4. Contribution variance analysis
    """

    def __init__(self) -> None:
        """Initialize contribution analyzer."""
        pass

    def analyze_absolute(
        self,
        segments: dict[str, float],
        metric_id: str,
    ) -> ContributionAnalysisResult:
        """Analyze absolute contributions.

        Args:
            segments: Dict of segment name to value
            metric_id: Metric being analyzed

        Returns:
            Contribution analysis result
        """
        total = sum(segments.values())

        if total == 0:
            return ContributionAnalysisResult(
                metric_id=metric_id,
                total_value=0,
                contributions=[],
            )

        contributions = []
        for name, value in segments.items():
            pct = (value / total) * 100 if total != 0 else 0
            contributions.append(Contribution(
                segment_name=name,
                segment_value=value,
                total_value=total,
                percentage=pct,
                contribution_type="absolute",
            ))

        # Sort by percentage descending
        contributions.sort(key=lambda x: x.percentage, reverse=True)

        return ContributionAnalysisResult(
            metric_id=metric_id,
            total_value=total,
            contributions=contributions,
            top_contributor=contributions[0].segment_name if contributions else None,
            analysis_type="absolute",
        )

    def analyze_change(
        self,
        current: dict[str, float],
        previous: dict[str, float],
        metric_id: str,
    ) -> ContributionAnalysisResult:
        """Analyze contribution to change.

        Args:
            current: Current period values
            previous: Previous period values
            metric_id: Metric being analyzed

        Returns:
            Contribution analysis result
        """
        all_segments = set(current.keys()) | set(previous.keys())

        current_total = sum(current.values())
        previous_total = sum(previous.values())
        total_change = current_total - previous_total

        contributions = []

        for segment in all_segments:
            curr_val = current.get(segment, 0)
            prev_val = previous.get(segment, 0)
            change = curr_val - prev_val

            # Contribution to total change
            if total_change != 0:
                pct = (change / total_change) * 100
            else:
                pct = 0

            contributions.append(Contribution(
                segment_name=segment,
                segment_value=change,
                total_value=total_change,
                percentage=pct,
                contribution_type="change",
            ))

        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x.percentage), reverse=True)

        return ContributionAnalysisResult(
            metric_id=metric_id,
            total_value=total_change,
            contributions=contributions,
            top_contributor=contributions[0].segment_name if contributions else None,
            analysis_type="change",
        )

    def analyze_variance(
        self,
        actual: dict[str, float],
        budget: dict[str, float],
        metric_id: str,
    ) -> ContributionAnalysisResult:
        """Analyze contribution to variance from budget.

        Args:
            actual: Actual values
            budget: Budgeted values
            metric_id: Metric being analyzed

        Returns:
            Contribution analysis result
        """
        all_segments = set(actual.keys()) | set(budget.keys())

        actual_total = sum(actual.values())
        budget_total = sum(budget.values())
        variance = actual_total - budget_total

        contributions = []

        for segment in all_segments:
            actual_val = actual.get(segment, 0)
            budget_val = budget.get(segment, 0)
            segment_variance = actual_val - budget_val

            if variance != 0:
                pct = (segment_variance / variance) * 100
            else:
                pct = 0

            contributions.append(Contribution(
                segment_name=segment,
                segment_value=segment_variance,
                total_value=variance,
                percentage=pct,
                contribution_type="variance",
            ))

        contributions.sort(key=lambda x: abs(x.percentage), reverse=True)

        return ContributionAnalysisResult(
            metric_id=metric_id,
            total_value=variance,
            contributions=contributions,
            top_contributor=contributions[0].segment_name if contributions else None,
            analysis_type="variance",
        )

    def get_top_contributors(
        self,
        result: ContributionAnalysisResult,
        n: int = 5,
    ) -> list[Contribution]:
        """Get top N contributors.

        Args:
            result: Contribution analysis result
            n: Number of top contributors

        Returns:
            Top N contributions
        """
        return result.contributions[:n]

    def get_concentration_ratio(
        self,
        result: ContributionAnalysisResult,
    ) -> dict[str, float]:
        """Calculate concentration ratios (e.g., top 20% of segments).

        Args:
            result: Contribution analysis result

        Returns:
            Concentration ratios
        """
        if not result.contributions:
            return {}

        sorted_conts = sorted(result.contributions, key=lambda x: x.percentage, reverse=True)
        total_pct = sum(c.percentage for c in sorted_conts)

        ratios = {}
        cumulative = 0.0
        for i, c in enumerate(sorted_conts, 1):
            cumulative += c.percentage
            if i in [1, 3, 5, 10, 20]:
                ratios[f"top_{i}"] = cumulative

        return ratios
