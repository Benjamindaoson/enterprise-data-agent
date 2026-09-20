"""Grafana integration for metrics and dashboards.

Provides:
- Prometheus metrics export
- Grafana dashboard JSON definitions
- Metrics collection and aggregation
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from eiw.observability.logging import get_structured_logger

logger = get_structured_logger(__name__, "grafana")


@dataclass
class GrafanaConfig:
    """Grafana/Prometheus configuration."""

    prometheus_port: int = 9090
    metrics_path: str = "/metrics"
    scrape_interval: int = 15  # seconds
    enabled: bool = False


@dataclass
class MetricValue:
    """Single metric value."""

    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class PrometheusMetrics:
    """Prometheus metrics exporter.

    Collects and exposes metrics in Prometheus format.
    """

    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._histogram_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        self._start_time = time.time()

    def counter_inc(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Increment value
            labels: Optional labels
        """
        key = self._make_key(name, labels)
        self._counters[key] += value

    def gauge_set(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric.

        Args:
            name: Metric name
            value: Value to set
            labels: Optional labels
        """
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def histogram_observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe a histogram value.

        Args:
            name: Metric name
            value: Observed value
            labels: Optional labels
        """
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

    def _make_key(self, name: str, labels: dict[str, str] | None = None) -> str:
        """Create metric key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _parse_key(self, key: str) -> tuple[str, dict[str, str]]:
        """Parse metric key into name and labels."""
        if "{" not in key:
            return key, {}
        name, labels_str = key.split("{", 1)
        labels_str = labels_str.rstrip("}")
        labels = {}
        for part in labels_str.split(","):
            k, v = part.split("=", 1)
            labels[k.strip()] = v.strip('"')
        return name, labels

    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        uptime = time.time() - self._start_time

        lines.append(f"# HELP process_uptime_seconds Process uptime in seconds")
        lines.append(f"# TYPE process_uptime_seconds gauge")
        lines.append(f"process_uptime_seconds {uptime:.2f}")

        # Counters
        for key, value in self._counters.items():
            name, labels = self._parse_key(key)
            help_line = f"# HELP {name} Counter metric"
            if not any(help_line in l for l in lines):
                lines.append(help_line)
                lines.append(f"# TYPE {name} counter")
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f'{name}{{{label_str}}} {value}')
            else:
                lines.append(f"{name} {value}")

        # Gauges
        for key, value in self._gauges.items():
            name, labels = self._parse_key(key)
            help_line = f"# HELP {name} Gauge metric"
            if not any(help_line in l for l in lines):
                lines.append(help_line)
                lines.append(f"# TYPE {name} gauge")
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f'{name}{{{label_str}}} {value}')
            else:
                lines.append(f"{name} {value}")

        # Histograms
        for key, values in self._histograms.items():
            name, labels = self._parse_key(key)
            lines.append(f"# HELP {name} Histogram metric")
            lines.append(f"# TYPE {name} histogram")

            if values:
                count = len(values)
                sum_val = sum(values)
                avg = sum_val / count

                # Bucket counts
                bucket_counts = {b: sum(1 for v in values if v <= b) for b in self._histogram_buckets}

                for bucket, cumulative_count in bucket_counts.items():
                    bucket_labels = {**labels, "le": str(bucket)} if labels else {"le": str(bucket)}
                    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(bucket_labels.items()))
                    lines.append(f'{name}_bucket{{{label_str}}} {cumulative_count}')

                # +Inf bucket
                inf_labels = {**labels, "le": "+Inf"} if labels else {"le": "+Inf"}
                inf_label_str = ",".join(f'{k}="{v}"' for k, v in sorted(inf_labels.items()))
                lines.append(f'{name}_bucket{{{inf_label_str}}} {count}')
                lines.append(f'{name}_sum {sum_val:.6f}')
                lines.append(f'{name}_count {count}')

        return "\n".join(lines) + "\n"


# Predefined metrics for Enterprise Data Agent
AGENT_METRICS = {
    # Task metrics
    "agent_tasks_total": "Total number of agent tasks",
    "agent_tasks_completed": "Completed agent tasks",
    "agent_tasks_failed": "Failed agent tasks",
    "agent_task_duration_seconds": "Task duration in seconds",

    # Executor metrics
    "executor_calls_total": "Total executor calls",
    "executor_call_duration_seconds": "Executor call duration",
    "executor_errors_total": "Executor errors",

    # LLM metrics
    "llm_requests_total": "Total LLM requests",
    "llm_request_duration_seconds": "LLM request duration",
    "llm_tokens_total": "Total tokens used",
    "llm_input_tokens": "Input tokens",
    "llm_output_tokens": "Output tokens",
    "llm_errors_total": "LLM errors",

    # Tool metrics
    "tool_calls_total": "Total tool calls",
    "tool_call_duration_seconds": "Tool call duration",
    "tool_call_errors_total": "Tool call errors",

    # NL2SQL metrics
    "nl2sql_generated_total": "Total SQL generations",
    "nl2sql_validated_total": "Total SQL validations",
    "nl2sql_repaired_total": "Total SQL repairs",
    "nl2sql_execution_total": "Total SQL executions",

    # HitL metrics
    "hitl_requests_total": "Total HitL requests",
    "hitl_responses_total": "Total HitL responses",
    "hitl_timeout_total": "HitL timeouts",

    # Evaluation metrics
    "eval_suite_runs_total": "Total evaluation suite runs",
    "eval_cases_passed": "Passed evaluation cases",
    "eval_cases_failed": "Failed evaluation cases",
}


class AgentMetricsCollector:
    """Collects and manages agent metrics."""

    def __init__(self):
        self._metrics = PrometheusMetrics()
        self._task_start_times: dict[str, float] = {}

    def record_task_start(self, task_id: str) -> None:
        """Record task start."""
        self._task_start_times[task_id] = time.time()
        self._metrics.counter_inc("agent_tasks_total", labels={"status": "started"})

    def record_task_complete(self, task_id: str) -> None:
        """Record task completion."""
        start_time = self._task_start_times.pop(task_id, time.time())
        duration = time.time() - start_time
        self._metrics.counter_inc("agent_tasks_total", labels={"status": "completed"})
        self._metrics.counter_inc("agent_tasks_completed")
        self._metrics.histogram_observe("agent_task_duration_seconds", duration)

    def record_task_error(self, task_id: str, error: str | None = None) -> None:
        """Record task error."""
        self._task_start_times.pop(task_id, None)
        self._metrics.counter_inc("agent_tasks_total", labels={"status": "failed"})
        self._metrics.counter_inc("agent_tasks_failed")
        if error:
            self._metrics.counter_inc("agent_errors", labels={"error_type": error[:50]})

    def record_executor_call(
        self,
        executor: str,
        tool: str,
        duration: float,
        success: bool = True,
    ) -> None:
        """Record executor call."""
        self._metrics.counter_inc(
            "executor_calls_total",
            labels={"executor": executor, "tool": tool}
        )
        self._metrics.histogram_observe(
            "executor_call_duration_seconds",
            duration,
            labels={"executor": executor, "tool": tool}
        )
        if not success:
            self._metrics.counter_inc(
                "executor_errors_total",
                labels={"executor": executor, "tool": tool}
            )

    def record_llm_request(
        self,
        provider: str,
        model: str,
        duration: float,
        input_tokens: int,
        output_tokens: int,
        success: bool = True,
    ) -> None:
        """Record LLM request."""
        self._metrics.counter_inc(
            "llm_requests_total",
            labels={"provider": provider, "model": model}
        )
        self._metrics.histogram_observe(
            "llm_request_duration_seconds",
            duration,
            labels={"provider": provider, "model": model}
        )
        self._metrics.counter_inc("llm_tokens_total", input_tokens + output_tokens)
        self._metrics.counter_inc("llm_input_tokens", input_tokens)
        self._metrics.counter_inc("llm_output_tokens", output_tokens)
        if not success:
            self._metrics.counter_inc("llm_errors_total", labels={"provider": provider})

    def record_tool_call(
        self,
        tool: str,
        duration: float,
        success: bool = True,
    ) -> None:
        """Record tool call."""
        self._metrics.counter_inc("tool_calls_total", labels={"tool": tool})
        self._metrics.histogram_observe(
            "tool_call_duration_seconds",
            duration,
            labels={"tool": tool}
        )
        if not success:
            self._metrics.counter_inc("tool_call_errors_total", labels={"tool": tool})

    def record_hitl_request(self, decision_type: str) -> None:
        """Record HitL request."""
        self._metrics.counter_inc("hitl_requests_total", labels={"type": decision_type})

    def record_hitl_response(self, decision_type: str, response_type: str) -> None:
        """Record HitL response."""
        self._metrics.counter_inc("hitl_responses_total", labels={"type": decision_type, "response": response_type})

    def record_hitl_timeout(self, decision_type: str) -> None:
        """Record HitL timeout."""
        self._metrics.counter_inc("hitl_timeout_total", labels={"type": decision_type})

    def export(self) -> str:
        """Export all metrics in Prometheus format."""
        return self._metrics.to_prometheus_format()


# Global metrics collector
_metrics_collector: AgentMetricsCollector | None = None


def get_metrics_collector() -> AgentMetricsCollector:
    """Get global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AgentMetricsCollector()
    return _metrics_collector


# Grafana dashboard JSON template
GRAFANA_DASHBOARD_TEMPLATE = {
    "title": "Enterprise Data Agent",
    "uid": "eda-dashboard",
    "panels": [
        {
            "title": "Task Success Rate",
            "type": "stat",
            "targets": [{"expr": "agent_tasks_completed / agent_tasks_total * 100"}],
            "fieldConfig": {"defaults": {"unit": "percent"}},
        },
        {
            "title": "Request Rate",
            "type": "timeseries",
            "targets": [{"expr": "rate(agent_tasks_total[5m])"}],
        },
        {
            "title": "LLM Latency",
            "type": "timeseries",
            "targets": [{"expr": "histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))"}],
            "fieldConfig": {"defaults": {"unit": "s"}},
        },
        {
            "title": "Token Usage",
            "type": "timeseries",
            "targets": [
                {"expr": "rate(llm_input_tokens[5m])", "legendFormat": "Input"},
                {"expr": "rate(llm_output_tokens[5m])", "legendFormat": "Output"},
            ],
        },
        {
            "title": "Executor Call Duration",
            "type": "timeseries",
            "targets": [{"expr": "histogram_quantile(0.95, rate(executor_call_duration_seconds_bucket[5m]))"}],
            "fieldConfig": {"defaults": {"unit": "s"}},
        },
        {
            "title": "HitL Response Rate",
            "type": "timeseries",
            "targets": [
                {"expr": 'rate(hitl_responses_total{response="approved"}[5m])', "legendFormat": "Approved"},
                {"expr": 'rate(hitl_responses_total{response="rejected"}[5m])', "legendFormat": "Rejected"},
                {"expr": 'rate(hitl_timeout_total[5m])', "legendFormat": "Timeout"},
            ],
        },
        {
            "title": "NL2SQL Pipeline",
            "type": "timeseries",
            "targets": [
                {"expr": "rate(nl2sql_generated_total[5m])", "legendFormat": "Generated"},
                {"expr": "rate(nl2sql_validated_total[5m])", "legendFormat": "Validated"},
                {"expr": "rate(nl2sql_execution_total[5m])", "legendFormat": "Executed"},
            ],
        },
        {
            "title": "Evaluation Results",
            "type": "stat",
            "targets": [
                {"expr": "eval_cases_passed"},
                {"expr": "eval_cases_failed"},
            ],
        },
    ],
}
