"""Anomaly Detection for Enterprise Data Agent.

Detects anomalies in data using multiple methods:
- Statistical thresholding (Z-score, IQR)
- Change point detection
- Contextual anomaly detection
- Time-series anomaly detection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AnomalyType(Enum):
    """Types of detected anomalies."""

    POINT = "point"           # Single point anomaly
    CONTEXTUAL = "contextual" # Anomaly given context
    COLLECTIVE = "collective" # Collection of anomalous points
    CHANGE_POINT = "change_point"  # Sudden change


class AnomalySeverity(Enum):
    """Severity of anomaly."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    """A detected anomaly."""

    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    metric_id: str
    timestamp: datetime
    value: float
    expected_value: float | None
    deviation: float  # How far from expected
    description: str
    possible_causes: list[str] = field(default_factory=list)


@dataclass
class AnomalyDetectionResult:
    """Result of anomaly detection."""

    metric_id: str
    total_points: int
    anomalies_found: int
    anomalies: list[Anomaly] = field(default_factory=list)
    baseline_mean: float | None = None
    baseline_std: float | None = None
    detection_method: str = "statistical"


class AnomalyDetector:
    """Detects anomalies in metrics.

    Supports multiple detection methods:
    1. Z-score thresholding
    2. IQR (Interquartile Range) method
    3. Moving average deviation
    4. Change point detection
    """

    def __init__(self, sensitivity: float = 2.0) -> None:
        """Initialize anomaly detector.

        Args:
            sensitivity: Z-score threshold for anomalies (default 2.0)
        """
        self.sensitivity = sensitivity

    def detect(
        self,
        data: list[dict[str, Any]],
        date_column: str,
        value_column: str,
        metric_id: str,
        method: str = "zscore",
    ) -> AnomalyDetectionResult:
        """Detect anomalies in data.

        Args:
            data: Time-series data
            date_column: Name of date column
            value_column: Name of value column
            metric_id: Metric being analyzed
            method: Detection method (zscore, iqr, moving_avg)

        Returns:
            Anomaly detection result
        """
        if not data:
            return AnomalyDetectionResult(
                metric_id=metric_id,
                total_points=0,
                anomalies_found=0,
            )

        # Sort by date
        sorted_data = sorted(data, key=lambda x: x.get(date_column, ""))
        values = [d.get(value_column, 0) for d in sorted_data]

        # Calculate baseline statistics
        baseline_mean = sum(values) / len(values)
        baseline_std = self._calculate_std(values)

        # Detect anomalies based on method
        if method == "zscore":
            anomalies = self._detect_zscore(sorted_data, values, metric_id)
        elif method == "iqr":
            anomalies = self._detect_iqr(sorted_data, values, metric_id)
        elif method == "moving_avg":
            anomalies = self._detect_moving_avg(sorted_data, values, metric_id)
        else:
            anomalies = self._detect_zscore(sorted_data, values, metric_id)

        return AnomalyDetectionResult(
            metric_id=metric_id,
            total_points=len(data),
            anomalies_found=len(anomalies),
            anomalies=anomalies,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            detection_method=method,
        )

    def _calculate_std(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance ** 0.5

    def _detect_zscore(
        self,
        data: list[dict[str, Any]],
        values: list[float],
        metric_id: str,
    ) -> list[Anomaly]:
        """Detect anomalies using Z-score method."""
        import uuid

        anomalies = []
        mean = sum(values) / len(values)
        std = self._calculate_std(values)

        if std == 0:
            return []

        for i, (d, v) in enumerate(zip(data, values)):
            z_score = (v - mean) / std

            if abs(z_score) > self.sensitivity:
                severity = self._get_severity(abs(z_score))
                deviation = abs(v - mean)

                anomalies.append(Anomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.POINT,
                    severity=severity,
                    metric_id=metric_id,
                    timestamp=d.get(d.get("__date_column", "date"), datetime.now()),
                    value=v,
                    expected_value=mean,
                    deviation=deviation,
                    description=f"Value {v:.2f} is {z_score:.1f} standard deviations from mean",
                    possible_causes=self._suggest_causes(v, mean, deviation),
                ))

        return anomalies

    def _detect_iqr(
        self,
        data: list[dict[str, Any]],
        values: list[float],
        metric_id: str,
    ) -> list[Anomaly]:
        """Detect anomalies using IQR method."""
        import uuid

        anomalies = []

        # Sort values
        sorted_values = sorted(values)
        n = len(sorted_values)

        # Calculate quartiles
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1

        # Calculate bounds
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        mean = sum(values) / len(values)

        for d, v in zip(data, values):
            if v < lower_bound or v > upper_bound:
                deviation = max(lower_bound - v, v - upper_bound, 0)

                anomalies.append(Anomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.POINT,
                    severity=AnomalySeverity.MEDIUM,
                    metric_id=metric_id,
                    timestamp=d.get(d.get("__date_column", "date"), datetime.now()),
                    value=v,
                    expected_value=mean,
                    deviation=deviation,
                    description=f"Value {v:.2f} is outside IQR bounds [{lower_bound:.2f}, {upper_bound:.2f}]",
                    possible_causes=["Data entry error", "Genuine extreme value", "Systematic change"],
                ))

        return anomalies

    def _detect_moving_avg(
        self,
        data: list[dict[str, Any]],
        values: list[float],
        metric_id: str,
    ) -> list[Anomaly]:
        """Detect anomalies using moving average deviation."""
        import uuid

        anomalies = []
        window_size = min(7, len(values) // 2)

        for i in range(window_size, len(values)):
            # Calculate moving average
            window = values[i - window_size:i]
            ma = sum(window) / len(window)
            std = self._calculate_std(window)

            v = values[i]
            if std > 0:
                z_score = (v - ma) / std

                if abs(z_score) > self.sensitivity:
                    severity = self._get_severity(abs(z_score))

                    anomalies.append(Anomaly(
                        anomaly_id=str(uuid.uuid4()),
                        anomaly_type=AnomalyType.CONTEXTUAL,
                        severity=severity,
                        metric_id=metric_id,
                        timestamp=data[i].get(data[i].get("__date_column", "date"), datetime.now()),
                        value=v,
                        expected_value=ma,
                        deviation=abs(v - ma),
                        description=f"Value {v:.2f} deviates {z_score:.1f}σ from moving average",
                        possible_causes=self._suggest_causes(v, ma, abs(v - ma)),
                    ))

        return anomalies

    def _get_severity(self, z_score: float) -> AnomalySeverity:
        """Determine anomaly severity based on Z-score."""
        if z_score > 5:
            return AnomalySeverity.CRITICAL
        elif z_score > 4:
            return AnomalySeverity.HIGH
        elif z_score > 3:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def _suggest_causes(
        self,
        value: float,
        expected: float,
        deviation: float,
    ) -> list[str]:
        """Suggest possible causes for an anomaly."""
        causes = []

        if expected != 0:
            pct_change = abs(value - expected) / abs(expected) * 100

            if pct_change > 100:
                causes.append("Major data spike or drop")
                causes.append("System error or data source issue")
            elif pct_change > 50:
                causes.append("Significant change in underlying metric")
                causes.append("Seasonal variation")
            else:
                causes.append("Normal fluctuation")
                causes.append("Measurement noise")

        causes.append("Requires manual investigation")

        return causes[:3]  # Return top 3 causes
