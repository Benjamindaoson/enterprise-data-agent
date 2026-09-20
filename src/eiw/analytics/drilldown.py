"""Drill-Down Analysis for Enterprise Data Agent.

Provides hierarchical drill-down analysis:
- Dimension hierarchy navigation
- Aggregation level stepping
- Zoom in/out functionality
- Cross-segment drilling
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DrillPath:
    """A drill-down path."""

    dimension: str
    from_level: str
    to_level: str
    from_value: str
    to_value: str
    metric_change: float  # Percentage change at this level


@dataclass
class DrillDownResult:
    """Result of drill-down analysis."""

    metric_id: str
    primary_dimension: str
    path: list[DrillPath] = field(default_factory=list)
    root_value: float
    leaf_values: dict[str, float] = field(default_factory=dict)
    analysis_summary: str


class DrillDownAnalyzer:
    """Performs drill-down analysis.

    This analyzer provides:
    1. Hierarchical dimension drilling
    2. Cross-segment analysis
    3. Root cause identification
    4. Aggregation level navigation
    """

    def __init__(self) -> None:
        """Initialize drill-down analyzer."""
        # Common dimension hierarchies
        self._hierarchies = {
            "region": ["country", "region", "state", "city", "store"],
            "product": ["category", "subcategory", "product_family", "product", "sku"],
            "time": ["year", "quarter", "month", "week", "day"],
            "customer": ["segment", "tier", "cohort", "individual"],
            "channel": ["channel_group", "channel", "subchannel"],
        }

    def drill_down(
        self,
        data: list[dict[str, Any]],
        dimension: str,
        metric_id: str,
        from_level: str | None = None,
        to_level: str | None = None,
    ) -> DrillDownResult:
        """Perform drill-down analysis.

        Args:
            data: Hierarchical data
            dimension: Dimension to drill down
            metric_id: Metric being analyzed
            from_level: Starting level (default: top level)
            to_level: Target level (default: most granular)

        Returns:
            Drill-down result
        """
        if dimension not in self._hierarchies:
            return DrillDownResult(
                metric_id=metric_id,
                primary_dimension=dimension,
                analysis_summary=f"No hierarchy defined for {dimension}",
            )

        hierarchy = self._hierarchies[dimension]

        if from_level is None:
            from_level = hierarchy[0]
        if to_level is None:
            to_level = hierarchy[-1]

        from_idx = hierarchy.index(from_level) if from_level in hierarchy else 0
        to_idx = hierarchy.index(to_level) if to_level in hierarchy else len(hierarchy) - 1

        # Calculate aggregate at each level
        aggregates = self._calculate_level_aggregates(data, dimension, hierarchy)

        # Build drill paths
        paths = []
        for i in range(from_idx, min(to_idx, len(hierarchy) - 1)):
            from_agg = aggregates.get(hierarchy[i], {})
            to_agg = aggregates.get(hierarchy[i + 1], {})

            # Calculate change
            from_total = sum(from_agg.values())
            to_total = sum(to_agg.values())

            change = 0.0
            if from_total != 0:
                change = ((to_total - from_total) / from_total) * 100

            paths.append(DrillPath(
                dimension=dimension,
                from_level=hierarchy[i],
                to_level=hierarchy[i + 1],
                from_value=hierarchy[i],
                to_value=hierarchy[i + 1],
                metric_change=change,
            ))

        # Get leaf values (most granular)
        leaf_agg = aggregates.get(to_level, {})

        return DrillDownResult(
            metric_id=metric_id,
            primary_dimension=dimension,
            path=paths,
            root_value=sum(aggregates.get(hierarchy[0], {}).values()),
            leaf_values=leaf_agg,
            analysis_summary=self._generate_summary(paths, leaf_agg),
        )

    def _calculate_level_aggregates(
        self,
        data: list[dict[str, Any]],
        dimension: str,
        hierarchy: list[str],
    ) -> dict[str, dict[str, float]]:
        """Calculate aggregates at each level."""
        aggregates: dict[str, dict[str, float]] = {level: {} for level in hierarchy}

        for row in data:
            # Get value
            value = row.get("value", 0)

            # Get dimension value (simplified - assumes column name matches)
            dim_value = row.get(dimension, "Unknown")

            # Aggregate at each level (simplified)
            for level in hierarchy:
                if level not in aggregates:
                    aggregates[level] = {}

                key = f"{dim_value}_{level}"
                aggregates[level][key] = aggregates[level].get(key, 0) + value

        return aggregates

    def _generate_summary(
        self,
        paths: list[DrillPath],
        leaf_values: dict[str, float],
    ) -> str:
        """Generate drill-down summary."""
        if not paths:
            return "No drill-down path available"

        parts = []

        for path in paths:
            direction = "increased" if path.metric_change > 0 else "decreased"
            parts.append(
                f"Drilling from {path.from_level} to {path.to_level}: "
                f"metric {direction} by {abs(path.metric_change):.1f}%"
            )

        if leaf_values:
            top_leaf = max(leaf_values.items(), key=lambda x: x[1])
            parts.append(f"Largest contributor: {top_leaf[0]} with value {top_leaf[1]:.2f}")

        return ". ".join(parts)

    def get_available_dimensions(self) -> list[str]:
        """Get dimensions with hierarchies."""
        return list(self._hierarchies.keys())

    def get_dimension_hierarchy(self, dimension: str) -> list[str]:
        """Get hierarchy for a dimension."""
        return self._hierarchies.get(dimension, [])
