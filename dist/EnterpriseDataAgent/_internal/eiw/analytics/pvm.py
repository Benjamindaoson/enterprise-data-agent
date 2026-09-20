"""Price Volume Analysis for Enterprise Data Agent.

Analyzes price-volume relationships:
- Price-volume correlation
- Price momentum analysis
- Volume confirmation
- Distribution analysis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PriceVolumeMetrics:
    """Price and volume metrics."""

    period: str
    avg_price: float
    avg_volume: float
    price_change: float  # Percentage
    volume_change: float  # Percentage
    price_volatility: float
    volume_volatility: float


@dataclass
class PVMAnalysisResult:
    """Result of price-volume analysis."""

    metric_id: str
    correlation: float
    is_confirmed: bool  # Volume confirms price trend
    price_momentum: str  # strong_up, up, neutral, down, strong_down
    volume_momentum: str
    summary: str
    segments: list[PriceVolumeMetrics] = field(default_factory=list)


class PriceVolumeAnalyzer:
    """Analyzes price-volume relationships.

    This analyzer provides:
    1. Correlation analysis
    2. Momentum assessment
    3. Trend confirmation
    4. Distribution analysis
    """

    def __init__(self) -> None:
        """Initialize PVM analyzer."""
        pass

    def analyze(
        self,
        data: list[dict[str, Any]],
        price_column: str,
        volume_column: str,
        metric_id: str,
    ) -> PVMAnalysisResult:
        """Analyze price-volume relationship.

        Args:
            data: Time-series data with price and volume
            price_column: Name of price column
            volume_column: Name of volume column
            metric_id: Metric being analyzed

        Returns:
            PVM analysis result
        """
        if not data:
            return PVMAnalysisResult(
                metric_id=metric_id,
                correlation=0.0,
                is_confirmed=False,
                price_momentum="neutral",
                volume_momentum="neutral",
                summary="No data available",
            )

        prices = [d.get(price_column, 0) for d in data]
        volumes = [d.get(volume_column, 0) for d in data]

        # Calculate correlation
        correlation = self._calculate_correlation(prices, volumes)

        # Calculate momentum
        price_change = self._calculate_change(prices)
        volume_change = self._calculate_change(volumes)

        price_momentum = self._classify_momentum(price_change)
        volume_momentum = self._classify_momentum(volume_change)

        # Determine if trend is confirmed
        is_confirmed = self._is_confirmed(price_change, volume_change)

        # Calculate volatility
        price_vol = self._calculate_volatility(prices)
        volume_vol = self._calculate_volatility(volumes)

        # Create segments
        segments = self._create_segments(
            data, price_column, volume_column,
            price_change, volume_change,
            price_vol, volume_vol
        )

        summary = self._generate_summary(
            price_change, volume_change, correlation, is_confirmed
        )

        return PVMAnalysisResult(
            metric_id=metric_id,
            correlation=correlation,
            is_confirmed=is_confirmed,
            price_momentum=price_momentum,
            volume_momentum=volume_momentum,
            summary=summary,
            segments=segments,
        )

    def _calculate_correlation(self, x: list[float], y: list[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = min(len(x), len(y))
        if n < 2:
            return 0.0

        x = x[:n]
        y = y[:n]

        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        x_denom = sum((x[i] - x_mean) ** 2 for i in range(n)) ** 0.5
        y_denom = sum((y[i] - y_mean) ** 2 for i in range(n)) ** 0.5

        if x_denom == 0 or y_denom == 0:
            return 0.0

        return numerator / (x_denom * y_denom)

    def _calculate_change(self, values: list[float]) -> float:
        """Calculate percentage change."""
        if len(values) < 2 or values[0] == 0:
            return 0.0

        return ((values[-1] - values[0]) / values[0]) * 100

    def _calculate_volatility(self, values: list[float]) -> float:
        """Calculate volatility (coefficient of variation)."""
        if not values:
            return 0.0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0

        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return (variance ** 0.5) / mean * 100

    def _classify_momentum(self, change_pct: float) -> str:
        """Classify momentum based on change percentage."""
        if change_pct > 10:
            return "strong_up"
        elif change_pct > 2:
            return "up"
        elif change_pct < -10:
            return "strong_down"
        elif change_pct < -2:
            return "down"
        else:
            return "neutral"

    def _is_confirmed(self, price_change: float, volume_change: float) -> bool:
        """Check if volume confirms price trend."""
        if price_change > 0 and volume_change > 0:
            return True
        elif price_change < 0 and volume_change < 0:
            return True
        elif abs(price_change) < 2:  # No strong trend
            return True
        return False

    def _create_segments(
        self,
        data: list[dict[str, Any]],
        price_col: str,
        volume_col: str,
        price_change: float,
        volume_change: float,
        price_vol: float,
        volume_vol: float,
    ) -> list[PriceVolumeMetrics]:
        """Create segment metrics."""
        # Create monthly/weekly segments
        segments = []
        window_size = max(1, len(data) // 4)

        for i in range(0, len(data), window_size):
            window = data[i:i + window_size]
            if not window:
                continue

            prices = [d.get(price_col, 0) for d in window]
            volumes = [d.get(volume_col, 0) for d in window]

            seg = PriceVolumeMetrics(
                period=f"Period {i // window_size + 1}",
                avg_price=sum(prices) / len(prices),
                avg_volume=sum(volumes) / len(volumes),
                price_change=price_change,
                volume_change=volume_change,
                price_volatility=price_vol,
                volume_volatility=volume_vol,
            )
            segments.append(seg)

        return segments

    def _generate_summary(
        self,
        price_change: float,
        volume_change: float,
        correlation: float,
        is_confirmed: bool,
    ) -> str:
        """Generate analysis summary."""
        parts = []

        if price_change > 0:
            parts.append(f"Price increased by {price_change:.1f}%")
        elif price_change < 0:
            parts.append(f"Price decreased by {abs(price_change):.1f}%")
        else:
            parts.append("Price remained stable")

        if volume_change > 0:
            parts.append(f"Volume up {volume_change:.1f}%")
        elif volume_change < 0:
            parts.append(f"Volume down {abs(volume_change):.1f}%")

        parts.append(f"Correlation: {correlation:.2f}")

        if is_confirmed:
            parts.append("Trend confirmed by volume")
        else:
            parts.append("Trend NOT confirmed by volume")

        return ". ".join(parts)
