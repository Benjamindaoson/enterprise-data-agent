"""Trend Analysis for Enterprise Data Agent.

Analyzes trends in time-series data:
- Direction identification (up, down, stable)
- Rate of change calculation
- Seasonality detection
- Trend significance testing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TrendDirection(Enum):
    """Direction of a trend."""

    UPWARD = "upward"
    DOWNWARD = "downward"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class TrendSegment:
    """A segment of a trend."""

    start_date: datetime
    end_date: datetime
    direction: TrendDirection
    slope: float  # Percentage change per period
    confidence: float  # 0-1


@dataclass
class SeasonalityPattern:
    """Detected seasonality pattern."""

    period: int  # Period length (e.g., 7 for weekly, 12 for monthly)
    amplitude: float  # Relative amplitude
    phase: float  # Phase offset
    confidence: float


@dataclass
class TrendResult:
    """Result of trend analysis."""

    metric_id: str
    overall_direction: TrendDirection
    overall_slope: float
    cagr: float  # Compound Annual Growth Rate
    volatility: float  # Standard deviation of changes
    segments: list[TrendSegment] = field(default_factory=list)
    seasonality: SeasonalityPattern | None = None
    significance: float = 1.0  # p-value based significance
    data_points: int = 0


class TrendAnalyzer:
    """Analyzes trends in time-series data.

    This analyzer provides:
    1. Trend direction identification
    2. Rate of change calculation
    3. Seasonality detection
    4. Trend significance testing
    """

    def __init__(self) -> None:
        """Initialize trend analyzer."""
        pass

    def analyze(
        self,
        data: list[dict[str, Any]],
        date_column: str,
        value_column: str,
        metric_id: str,
    ) -> TrendResult:
        """Analyze trends in data.

        Args:
            data: Time-series data points
            date_column: Name of the date column
            value_column: Name of the value column
            metric_id: Metric being analyzed

        Returns:
            Trend analysis result
        """
        if not data:
            return TrendResult(
                metric_id=metric_id,
                overall_direction=TrendDirection.STABLE,
                overall_slope=0.0,
                cagr=0.0,
                volatility=0.0,
            )

        # Sort by date
        sorted_data = sorted(data, key=lambda x: x.get(date_column, ""))

        values = [d.get(value_column, 0) for d in sorted_data]
        dates = [d.get(date_column) for d in sorted_data]

        # Calculate overall metrics
        overall_direction, overall_slope = self._calculate_direction(values)
        cagr = self._calculate_cagr(values)
        volatility = self._calculate_volatility(values)
        significance = self._calculate_significance(values)

        # Detect segments
        segments = self._detect_segments(values, dates)

        # Detect seasonality
        seasonality = self._detect_seasonality(values)

        return TrendResult(
            metric_id=metric_id,
            overall_direction=overall_direction,
            overall_slope=overall_slope,
            cagr=cagr,
            volatility=volatility,
            segments=segments,
            seasonality=seasonality,
            significance=significance,
            data_points=len(data),
        )

    def _calculate_direction(
        self,
        values: list[float],
    ) -> tuple[TrendDirection, float]:
        """Calculate overall trend direction and slope."""
        if len(values) < 2:
            return TrendDirection.STABLE, 0.0

        # Linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return TrendDirection.STABLE, 0.0

        slope = numerator / denominator

        # Convert to percentage change per period
        if y_mean != 0:
            slope_pct = slope / y_mean * 100
        else:
            slope_pct = 0.0

        # Determine direction
        if abs(slope_pct) < 0.1:  # Less than 0.1% per period
            direction = TrendDirection.STABLE
        elif slope_pct > 0:
            direction = TrendDirection.UPWARD
        else:
            direction = TrendDirection.DOWNWARD

        return direction, slope_pct

    def _calculate_cagr(self, values: list[float]) -> float:
        """Calculate Compound Annual Growth Rate."""
        if len(values) < 2 or values[0] == 0:
            return 0.0

        start_value = values[0]
        end_value = values[-1]
        periods = len(values) - 1

        if start_value <= 0 or periods <= 0:
            return 0.0

        cagr = ((end_value / start_value) ** (1 / periods) - 1) * 100
        return cagr

    def _calculate_volatility(self, values: list[float]) -> float:
        """Calculate volatility (std dev of period changes)."""
        if len(values) < 3:
            return 0.0

        changes = []
        for i in range(1, len(values)):
            if values[i - 1] != 0:
                change = (values[i] - values[i - 1]) / values[i - 1]
                changes.append(change)

        if not changes:
            return 0.0

        mean_change = sum(changes) / len(changes)
        variance = sum((c - mean_change) ** 2 for c in changes) / len(changes)
        return variance ** 0.5

    def _calculate_significance(self, values: list[float]) -> float:
        """Calculate trend significance (simplified R-squared)."""
        if len(values) < 3:
            return 0.0

        n = len(values)
        y_mean = sum(values) / n

        # Calculate R-squared
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))

        x_mean = (n - 1) / 2
        ss_reg = sum(
            ((i - x_mean) ** 2) for i in range(n)
        )

        if ss_tot == 0:
            return 0.0

        # Simplified R-squared
        r_squared = 1 - (ss_tot - ss_reg) / ss_tot
        return max(0.0, min(1.0, r_squared))

    def _detect_segments(
        self,
        values: list[float],
        dates: list[Any],
    ) -> list[TrendSegment]:
        """Detect distinct trend segments."""
        if len(values) < 3:
            return []

        segments = []
        window_size = max(2, len(values) // 5)

        for i in range(0, len(values) - window_size, window_size):
            window_values = values[i:i + window_size]
            direction, slope = self._calculate_direction(window_values)

            if len(dates) > i + window_size - 1:
                segment = TrendSegment(
                    start_date=dates[i],
                    end_date=dates[i + window_size - 1],
                    direction=direction,
                    slope=slope,
                    confidence=0.7,
                )
                segments.append(segment)

        return segments

    def _detect_seasonality(
        self,
        values: list[float],
    ) -> SeasonalityPattern | None:
        """Detect seasonality in data."""
        # Simple autocorrelation-based seasonality detection
        if len(values) < 12:
            return None

        # Check for weekly pattern (lag 7)
        # Check for monthly pattern (lag 4 for weekly data, lag 12 for monthly)
        for period in [4, 7, 12, 52]:
            if len(values) > period * 2:
                correlation = self._autocorrelation(values, period)
                if correlation > 0.5:
                    return SeasonalityPattern(
                        period=period,
                        amplitude=correlation,
                        phase=0,
                        confidence=correlation,
                    )

        return None

    def _autocorrelation(self, values: list[float], lag: int) -> float:
        """Calculate autocorrelation at a specific lag."""
        if len(values) <= lag:
            return 0.0

        n = len(values) - lag
        mean = sum(values) / len(values)

        c0 = sum((values[i] - mean) ** 2 for i in range(len(values))) / len(values)

        if c0 == 0:
            return 0.0

        c_lag = sum(
            (values[i] - mean) * (values[i + lag] - mean)
            for i in range(n)
        ) / n

        return c_lag / c0
